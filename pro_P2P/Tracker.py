from Proxy import Proxy


class Tracker:
    def __init__(self, upload_rate=10000, download_rate=10000, port=None):
        self.proxy = Proxy(upload_rate, download_rate, port)
        self.files = {}
        self.file_name = {}
        self.port = {}

    def __send__(self, data: bytes, dst: (str, int)):
        self.proxy.sendto(data, dst)

    def __recv__(self, timeout=None) -> (bytes, (str, int)):
        return self.proxy.recvfrom(timeout)

    def response(self, data: str, address: (str, int)):
        self.__send__(data.encode(), address)

    def start(self):
        while True:
            msg, frm = self.__recv__()
            print(msg)
            msg, client = msg.decode(), "(\"%s\", %d)" % frm

            if msg.startswith("REGISTER"):
                lines = msg.split(" ")
                fid = lines[0].split("-")[1]
                file_name = lines[0].split("-")[2]
                num = int(lines[0].split("-")[3])

                if fid not in self.file_name:
                    self.file_name[fid] = []
                self.file_name[fid].append(file_name)

                if fid not in self.files:
                    self.files[fid] = []
                for i in range(0,num):
                    part_name = lines[i+1]
                    if part_name not in self.files[fid]:
                        self.files[fid].append(part_name)
                    if part_name not in self.port:
                        self.port[part_name] = []
                    self.port[part_name].append(frm)
                self.response("Success register", frm)

            elif msg.startswith("QUERY"):
                fid = msg.split('-')[1]
                for i in self.files[fid]:
                    res = "OWNER"+" "+str(self.file_name[fid][0]).replace('[','').replace(']','').replace("'","")+" "+str(i)+" "+("%s" % str(self.port[i])).replace(' ', '').replace('[','').replace(']','').replace('\'','').replace('(','').replace(')','-').replace('-,','-') + " " +str(len(self.files[fid]))
                    self.__send__(res.encode(),frm)

            elif msg.startswith("CANCEL"):
                fid = msg.split('-')[1]
                for i in self.files[fid]:
                    for j in self.port[i]:
                        if str(frm[0]) in str(j) and str(frm[1]) in str(j):
                            self.port[i].remove(j)
                # if client in self.files[fid]:
                #     self.files[fid].remove(client)
                self.response("CANCEL Success", frm)

            elif msg.startswith("CLOSE"):
                for i in self.port:
                    for j in self.port[i]:
                        if str(frm[0]) in str(j) and str(frm[1]) in str(j):
                            self.port[i].remove(j)
                self.response("CLOSE Success", frm)
                # for f in self.files:
                #     for client in self.files[f]:
                #         if client == "(\"%s\", %d)" % frm:
                #             self.files[f].remove(client)


if __name__ == '__main__':
    print("Tracker starts working!")
    tracker = Tracker(port=10086)
    tracker.start()
