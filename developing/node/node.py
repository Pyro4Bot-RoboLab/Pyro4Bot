#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ____________developed by paco andres____________________
# ________in collaboration with cristian vazquez _________

import sys
import os
import time
import pprint
from libs import config, control, utils, uriresolver
from libs.exceptions import Errornode
from multiprocessing import Process, Pipe, Queue
import traceback
import Pyro4
import Pyro4.naming as nm
from termcolor import colored

BIGBROTHER_PASSWORD = "PyRobot"
ROBOT_PASSWORD = "default"



def import_class(list_class):
    """ Import necesary packages for robot"""
    try:
        print(colored("____________IMPORTING CLASS_______________________",
                      'yellow'))
        for c in sorted(list_class):
            print colored("CLASS", "cyan"), "%s: from %s import %s" % (c[2], c[0], c[1])
            exec("from %s import %s" % (c[0], c[1]), globals())
    except Exception:
        print("ERROR IMPORTING CLASS:", c[0] + "/" + c[1] + "." + c[2])
        traceback.print_exc()
        exit(0)

# ___________________CLASS NODERB________________________________________


class NODERB (object):
    # revisar la carga posterior de parametros json
    def __init__(self, filename="", json=None):
        if json is None:
            json = {}

        self.filename = filename  # Json file
        self.N_conf = config.Config(filename=filename, json=json)  # Config from Json
        self.load_node(self, PROCESS={}, **self.N_conf.node)
        import_class(self.N_conf.module_cls())

        self.URI = None  # URIProxy for internal uri resolver
        self.URI_resolv = None  # Just URI
        self.URI_object = self.load_uri_resolver()  # Object resolver location

        self.load_robot()

        self.create_server_node()

    @control.load_node
    def load_node(self, data, **kwargs):
        global ROBOT_PASSWORD
        ROBOT_PASSWORD = self.name
        print(colored("NOTIFIER", "cyan") + (":Starting System PyRobot on Ethernet device %s IP: %s with password: %s" % (colored(self.ethernet, 'yellow'), colored(self.ip, 'yellow'), colored(ROBOT_PASSWORD, 'yellow'))))
        print(colored("NOTIFIER", "cyan") + (":Node config loaded for filename:%s" % (colored(self.filename, 'yellow'))))
        self.PROCESS = {}
        self.sensors = self.N_conf.sensors

    def load_uri_resolver(self):
        uri_r = uriresolver.uriresolver(self.N_conf.node,
                                        password=ROBOT_PASSWORD)
        self.URI_resolv, self.URI = uri_r.register_uriresolver()
        return uri_r

    def load_robot(self):
        print(colored("_________STARTING PYRO4BOT OBJECT___________________", "yellow"))
        for k in self.N_conf.whithout_deps():  # No dependencies
            self.start__object(k, self.sensors[k])
        object_robot = self.N_conf.with_deps()
        for k in object_robot:
            self.sensors[k]["_local_trys"] = 25
            self.sensors[k]["_remote_trys"] = 5

        while object_robot != []:
            k = object_robot.pop(0)
            self.sensors[k]["nr_local"], self.sensors[k]["nr_remote"] = self.N_conf.local_remote(
                k)
            st_local, st_remote = self.check_deps(k)
            if st_local == "ERROR":
                print "[%s]  STARTING %s Error in locals %s" % (colored(st_local, 'red'), k, self.sensors[k]["nr_local"])
                continue
            if st_remote == "ERROR":
                print "[%s]  STARTING %s Error in remotes %s" % (colored(st_remote, 'red'), k, self.sensors[k]["nr_remote"])
                continue

            if st_local == "WAIT" or st_remote == "WAIT":
                object_robot.append(k)
                continue
            if st_local == "OK":
                del(self.sensors[k]["nr_local"])
                del(self.sensors[k]["_local_trys"])
                if st_remote == "OK":
                    del(self.sensors[k]["_remote_trys"])
                    del(self.sensors[k]["nr_remote"])
                self.sensors[k]["_REMOTE_STATUS"] = st_remote
                self.start__object(k, self.sensors[k])

    def check_local_deps(self, obj):
        check_local = "OK"
        for d in obj["nr_local"]:
            uri = self.URI.wait_available(d, ROBOT_PASSWORD)
            if uri is not None:
                obj["_local"].append(uri)
            else:
                obj["_local_trys"] -= 1
                if obj["_local_trys"] < 0:
                    check_local = "ERROR"
                    break
                else:
                    check_local = "WAIT"
                    break
        return check_local

    def check_remote_deps(self, obj):
        check_remote = "OK"
        for d in obj["nr_remote"]:
            uri = self.URI.wait_resolv_remotes(d)
            if uri is None:
                check_remote = "ERROR"
                break
            if uri == d:
                obj["_remote_trys"] -= 1
                if obj["_remote_trys"] < 0:
                    check_remote = "WAITING"
                    break
                else:
                    check_remote = "WAIT"
                    break
            else:
                obj["_remote"].append(uri)
        return check_remote
    print("STARTING NODERB")

    def check_deps(self, k):
        self.sensors[k]["_local"] = []
        self.sensors[k]["_remote"] = []
        check_local = self.check_local_deps(self.sensors[k])
        check_remote = self.check_remote_deps(self.sensors[k])
        return check_local, check_remote

    def start__object(self, name, obj):
        serv_pipe, client_pipe = Pipe()
        if "_local" not in obj:
            obj["_local"] = []
        if "_remote" not in obj:
            obj["_remote"] = []
        if name not in self.PROCESS:
            self.PROCESS[name] = []
            obj["pyro4id"] = self.URI.new_uri(name, obj["mode"])
            obj["name"] = name
            obj["uriresolver"] = self.URI_resolv
            q = Queue()
            self.PROCESS[name].append(obj["pyro4id"])
            self.PROCESS[name].append(
                Process(name=name, target=self.pyro4bot__object, args=(obj, client_pipe,q)))
            self.PROCESS[name][1].start()
            self.PROCESS[name].append(self.PROCESS[name][1].pid)
            status = serv_pipe.recv()
            self.PROCESS[name].append(status)
            self.PROCESS[name].append(q.get())
            if status == "OK":
                st = colored(status, 'green')
            if status == "FAIL":
                st = colored(status, 'red')
            if status == "WAITING":
                st = colored(status, 'yellow')
            print "[%s]  STARTING %s" % (st, obj["pyro4id"])
        else:
            print("ERROR: " + name + " is runing")

    def pyro4bot__object(self, d, proc_pipe, q):
        """ doc string for mi huevos"""
        (name_ob, ip, ports) = utils.uri_split(d["pyro4id"])
        try:
            daemon = Pyro4.Daemon(host=ip, port=ports)
            daemon._pyroHmacKey = bytes(ROBOT_PASSWORD)
            uri = daemon.register(eval(d["cls"])(data=[], **d), objectId=name_ob)
            exposed = Pyro4.core.DaemonObject(daemon).get_metadata(name_ob, True)
            q.put(exposed)
            if d.has_key("_REMOTE_STATUS") and d["_REMOTE_STATUS"] == "WAITING":
                proc_pipe.send("WAITING")
            else:
                proc_pipe.send("OK")
            daemon.requestLoop()
            print("[%s] Shuting %s" % (colored("Down", 'green'), d["pyro4id"]))
        except Exception as e:
            proc_pipe.send("FAIL")
            print("ERROR: creating sensor robot object: " + d["pyro4id"])
            print utils.format_exception(e)
            # raise

    def create_server_node(self):
        uri = None
        try:
            self.port_node = utils.get_free_port(self.port_node)
            daemon = Pyro4.Daemon(host=self.ip, port=self.port_node)
            daemon._pyroHmacKey = bytes(ROBOT_PASSWORD)
            # Registering NODE
            uri = daemon.register(self, objectId=self.name)
            # Registering NODE on nameserver
            self.URI.register_robot_on_nameserver(uri)
            # Printing info
            print(colored("____________STARTING PYRO4BOT %s_______________________" % self.name, "yellow"))
            print("[%s]  PYRO4BOT: %s" % (colored("OK", 'green'), uri))
            self.print_process()
            daemon.requestLoop()
        except Exception:
            print("ERROR: create_server_node in node.py")
            raise

    @Pyro4.expose
    def get_uris(self):
        return self.URI.list_uris()

    @Pyro4.expose
    def get_name_uri(self, name):
        # print self.URI.list_uris()
        if name in self.PROCESS:
            uri = self.URI.get_uri(name)
            status = self.PROCESS[name][3]
            return uri, status
        else:
            return None, "down"

    @Pyro4.expose
    def print_process(self):
        for k, v in self.PROCESS.iteritems():
            name = v[0]
            pid = str(v[2])
            status = str("[" + colored(v[3], 'green') + "]")
            print(status.ljust(17, " ") + pid + name.rjust(50, "."))
            print(v[-1])

    @Pyro4.expose
    def get_docstring(self,pyro4id,methods):
        """hola"""
        print pyro4id, methods
        p = Pyro4.Proxy(pyro4id)
        for k,met in methods.iteritems():
            for m in met:
                try:
                    print k,m,p
                    print(eval("p.{}.__doc__".format(m)))
                except Exception:
                    raise




if __name__ == "__main__":
    pass
