import Pyro4
from node.libs import utils
import time
from node.libs.publication import Publication
from node.libs.subscription import Subscription, dict_to_class
import threading
from threading import Thread
from termcolor import colored
from node.libs.botlogging import botlogging
from ordered_set import OrderedSet

SECS_TO_CHECK_STATUS = 5


# DECORATORS

# Threaded function snippet


def threaded(fn):
    """To use as decorator to make a function call threaded."""

    def wrapper(*args, **kwargs):
        thread = Thread(target=fn, args=args, name=fn.__name__, kwargs=kwargs)
        thread.start()
        return thread

    return wrapper


def Pyro4bot_Loader(clss, **kwargs):
    """ Decorator for load Json options in Pyro4bot objects
        init superclass control
    """
    original_init = clss.__init__
    supes = OrderedSet(clss.__mro__[::-1])
    supes.pop()

    def init(self):
        for k, v in kwargs.items():
            setattr(self, k, v)
        for x in supes:
            try:
                x.__init__(x)
            except:
                pass
        original_init(self)

    clss.__init__ = init
    return clss


def flask(*args_decorator):
    def flask_decorator(func):
        original_doc = func.__doc__
        if func.__doc__ is None:
            original_doc = ""
        if len(args_decorator) % 2 == 0:  # Tuplas
            for i in range(0, len(args_decorator), 2):
                original_doc += "\n@type:" + \
                                args_decorator[i] + "\n@count:" + \
                                str(args_decorator[i + 1])
        elif len(args_decorator) == 1:
            original_doc += "\n @type:" + \
                            args_decorator[0] + "\n@count:" + \
                            str(func.__code__.co_argcount - 1)

        if "@type:actuator" in original_doc:
            li = list(func.__code__.co_varnames)
            del li[0]
            original_doc += "\n@args_names:" + str(li)

        func.__doc__ = original_doc

        def func_wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        func_wrapper.__doc__ = original_doc
        return func_wrapper

    return flask_decorator


def timing(f):
    def wrap(*args):
        time1 = time.time()
        ret = f(*args)
        time2 = time.time()
        print('%s function took %0.3f ms' % (f.__name__, (time2 - time1) * 1000.0))
        return ret

    return wrap


class Control(botlogging.Logging):
    """ This class provide threading functionality to all object in node.
        Init workers Threads and PUB/SUB thread"""

    def __init__(self):
        super(Control, self).__init__()
        # before start worker assing ttys for output and errs
        if hasattr(self, "tty_out"):
            self.set_tty_err()
        if hasattr(self, "tty_err"):
            self.set_tty_out()
        self.mutex = threading.Lock()
        self.workers = []
        if "worker_run" not in self.__dict__:
            self.worker_run = True

    def __check_start__(self):
        while (self._REMOTE_STATUS != "OK" or
               (self._REMOTE_STATUS == "ASYNC" and
                not self._resolved_remote_deps)):
            time.sleep(SECS_TO_CHECK_STATUS)

    @threaded
    def start_worker(self, fn, *args):
        """ Start all workers daemon"""
        self.__check_start__()
        # before start worker assign ttys for output and errs
        self.set_tty_err()
        self.set_tty_out()
        if type(fn) not in (list, tuple):
            fn = (fn,)

        if self.worker_run:
            for func in fn:
                name = self.name + "." + func.__name__
                t = threading.Thread(target=func, name=name, args=args)
                t.setDaemon(True)
                self.workers.append(t)
                t.start()
        # for t in self.workers:
        #    t.start()

    @threaded
    def start_thread(self, fn, *args):
        """ Start all workers daemon"""
        self.__check_start__()
        if self.worker_run:
            name = self.name + "." + fn.__name__
            t = threading.Thread(target=fn, name=name, args=args)
            t.setDaemon(True)
            self.workers.append(t)
            t.start()

    # Publication methods
    @threaded
    def start_publisher(self, publication, frec=0.01):
        """ Start publisher daemon"""
        self.threadpublisher = False
        if isinstance(publication, Publication):
            self.threadpublisher = True
            t = threading.Thread(target=self.thread_publisher,
                                 args=(publication, frec),
                                 name=self.name + ".publisher")
            t.setDaemon(True)
            self.workers.append(t)
            t.start()
        else:
            self.L_error("Can not publish to object other than publication {}".format(publication))

    def thread_publisher(self, publication, frec):
        """Publish the publication in the subscriber list."""
        self.__check_start__()
        self.L_info("[FG][LOCAL] Starting Publisher")
        if not hasattr(self, 'subscriptors'):
            self.subscriptors = {}
        while self.threadpublisher:
            value = publication.get()
            try:
                subscriptors = self.subscriptors.copy()
                for key in subscriptors.keys():  # Key has an attribute to publish
                    subscriptors = self.subscriptors[key]
                    try:
                        if key in value:
                            for s in subscriptors:
                                # print("publicando", key, value[key], "-> ", s.subscripter_uri)
                                try:
                                    s.subscripter.publication(s.subscripter_attr, value[key])
                                except (Pyro4.errors.ConnectionClosedError, Pyro4.errors.CommunicationError):
                                    # print(
                                    #     "Can not connect to the subscriber: {}".format(s))
                                    self.subscriptors[key] = [
                                        sub for sub in self.subscriptors[key] if sub.id != s.id]
                                except Exception as ex:
                                    template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                                    print(template.format(type(ex).__name__, ex.args))
                                    # del self.subscriptors[key]

                    except TypeError:
                        print("Invalid argument.")
                        raise
                        exit()
            except Exception as e:
                print(utils.format_exception(e))
                raise
            time.sleep(frec)

    # Subscription methods
    @threaded
    def start_subscription(self, target, target_attr, subscripter_attr=None, subscripter_password=None):
        """Send a subscription request to the object given by parameter."""
        try:
            s = Subscription(target, target_attr,
                             subscripter_attr, subscripter_password)
            s.subscripter_uri = self.pyro4id
            t = threading.Thread(target=self.thread_subscriber,
                                 args=(s,),
                                 name=self.name + ".subcription")
            t.setDaemon(True)
            self.workers.append(t)
            t.start()

        except Exception:
            print("[ERROR] start_subscription. Error sending {}".format(target))
            raise

    def thread_subscriber(self, subscription):
        self.__check_start__()
        """Send a subscription request to the identifier given by parameter."""
        # print("-- Soy {} y mando esta subscription: {} ".format(
        # self.botname+"."+self.name, subscription))
        try:
            if hasattr(self, subscription.target):  # Locals
                x = getattr(self, subscription.target)
                x.subscribe(subscription.get())  # Sending as dict
                self.L_info("[FG][LOCAL] Subscribed to: {}".format(
                    subscription.target))
            else:  # Remotes
                connected = False
                while not connected:
                    if subscription.target in self.deps:
                        try:
                            if isinstance(self.deps[subscription.target], list):
                                if "." in subscription.target:
                                    target = subscription.target.split(".")
                                    if target[0].count("*") == 1 and target[1] and target[1].count("*") == 0:
                                        added_list = []
                                        while self.worker_run:
                                            for dp in self.deps[subscription.target]:
                                                if dp not in added_list:
                                                    try:
                                                        # print "Mando suscripcion a {}".format(dp)
                                                        dp.subscribe(subscription.get())
                                                        added_list.append(dp)
                                                    except Exception as ex:
                                                        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                                                        print(template.format(type(ex).__name__, ex.args))
                                for dp in self.deps[subscription.target]:
                                    try:
                                        dp.subscribe(subscription.get())
                                    except Exception as ex:
                                        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                                        print(template.format(type(ex).__name__, ex.args))
                            else:
                                self.deps[subscription.target].subscribe(
                                    subscription.get())
                                print(colored("{}: [REMOTE] Subscribed to: {}".format(
                                    self.name, subscription.target), "green"))
                            connected = True
                        except Exception:
                            pass
                            time.sleep(10)
                    time.sleep(2)
        except Exception:
            print("ERROR: in subscription: {}".format(subscription))
            raise

    @Pyro4.expose
    def subscribe(self, dict_sub):
        """ Receive a request for subscription from an object and save data in dict subscribers
            Data structure store one item subscription (key) and subscribers proxy list """
        subscription = dict_to_class(dict_sub)
        if not hasattr(self, 'subscriptors'):
            self.subscriptors = {}
        if not hasattr(self, 'id_publications'):
            self.id_publications = 0
        else:
            self.id_publications += 1

        try:
            if subscription.target_attr not in self.subscriptors:
                self.subscriptors[subscription.target_attr] = []
            subscription.id = self.id_publications

            proxy = self.__dict__["uriresolver"].get_proxy(
                subscription.subscripter_uri) if subscription.subscripter_password is None else self.__dict__[
                "uriresolver"].get_proxy(subscription.subscripter_uri, passw=subscription.subscripter_password)

            subscription.subscripter = proxy
            self.subscriptors[subscription.target_attr].append(subscription)
            # print("-- Soy {} y recibo correctamente esta suscripcion: {}".format(self.botname+"."+self.name, subscription))
            return True
        except Exception as ex:
            print("[subscribe] " + str(subscription))
            template = "[subscribe] An exception of type {0} occurred. Arguments:\n{1!r}"
            print(template.format(type(ex).__name__, ex.args))
            time.sleep(2)

    @Pyro4.oneway
    @Pyro4.expose
    def publication(self, key, value):
        # print "publication", key, value
        """ Is used to public in this object a item value """
        try:
            if hasattr(self, key):
                x = getattr(self, key)
                if isinstance(x, dict) and isinstance(value, dict):
                    x.update(value)
                # elif isinstance(x, list) and isinstance(value, list):
                #     setattr(self, key, list(set().union(x, value)))
                else:
                    setattr(self, key, value)
            else:
                setattr(self, key, value)
        except Exception:
            raise

    def adquire(self):
        self.mutex.adquire()

    def release(self):
        self.mutex.release()

    def stop(self):
        self.worker_run = False

    @Pyro4.expose
    def get_pyroid(self):
        return self.pyro4id

    @Pyro4.expose
    def __exposed__(self):
        return self.exposed

    @Pyro4.expose
    def __docstring__(self):
        return self.docstring

    @Pyro4.expose
    def get_class(self):
        return self._dict__[cls]

    @Pyro4.expose
    @Pyro4.callback
    def add_resolved_remote_dep(self, dep):
        # print(colored("New remote dep! {}, type: {}".format(dep, type(dep)), "green"))
        if isinstance(dep, dict):
            k = list(dep.keys())[0]
            proxy_lst = []
            try:
                if isinstance(dep[k], list):
                    for u in dep[k]:
                        if u not in self._resolved_remote_deps:
                            (name, _, _) = utils.uri_split(u)
                            proxy_lst.append(utils.get_pyro4proxy(u, name.split(".")[0]))
                            self._resolved_remote_deps.append(u)
                    if k in self.deps and isinstance(self.deps[k], list):
                        self.deps[k].extend(proxy_lst)
                    else:
                        self.deps[k] = proxy_lst
                else:
                    if dep[k] not in self._resolved_remote_deps:
                        (name, _, _) = utils.uri_split(dep[k])
                        self.deps[k] = utils.get_pyro4proxy(dep[k], name.split(".")[0])
                        self._resolved_remote_deps.append(dep[k])
                if self._unr_remote_deps is not None:
                    if k in self._unr_remote_deps:
                        self._unr_remote_deps.remove(k)
            except Exception as ex:
                template = "[control.add_resolved_remote_dep()] An exception of type {0} occurred. Arguments:\n{1!r}"
                print(template.format(type(ex).__name__, ex.args))
            self.check_remote_deps()
        else:
            print("Error in control.add_resolved_remote_dep(): No dict", dep)

    def check_remote_deps(self):
        status = True
        if self._unr_remote_deps is not None and self._unr_remote_deps:
            for unr in self._unr_remote_deps:
                if "*" not in unr:
                    status = False
        for k in self.deps.keys():
            try:
                if isinstance(self.deps[k], list):
                    for prx in self.deps[k]:
                        if prx._pyroHandshake != "hello":
                            status = False
                else:
                    if self.deps[k]._pyroHandshake != "hello":
                        status = False
            except Exception as ex:
                print("Error connecting to dep: {} ".format(k))
                template = "[check_remote_deps] An exception of type {0} occurred. Arguments:\n{1!r}"
                print(template.format(type(ex).__name__, ex.args))
                status = False

        if status:
            self._REMOTE_STATUS = "OK"
            try:
                self.node.status_changed()
            except Exception as e:
                print("Error in control.check_remote_deps: " + str(e))

        return self._REMOTE_STATUS

    @Pyro4.expose
    def get_status(self):
        """
        Return OK if all remotes are satisficed
        else return PENDING
        """
        return self._REMOTE_STATUS

    @Pyro4.expose
    def set_tty_out(self, tty=""):
        """
        Set terminal for outputs prints
        if not tty parameter set default component tty.
        check errror in tty returning false if it can't be assigned
        """
        if tty == "":
            return utils.set_tty_out(self.tty_out)
        else:
            return utils.set_tty_out(tty)

    @Pyro4.expose
    def set_tty_err(self, tty=""):
        """
        Set terminal for errors prints
        if not tty parameter set default component tty.
        check errror in tty returning false if it can't be assigned
        """
        if tty == "":
            return utils.set_tty_err(self.tty_err)
        else:
            return utils.set_tty_err(tty)
