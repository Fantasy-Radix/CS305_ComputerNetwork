import hashlib
import threading
import time
from Proxy import Proxy

Register_Head = "REGISTER"
Want_Head = "WANT"
Query_Head = "QUERY"
Owner_Head = "OWNER"
Transmit_Head = "TRANSMIT"
Close_Head = "CLOSE"
Cancel_Head = "CANCEL"


def hash_fid(file_path, Bytes=64000): # 65536会超
    md5 = hashlib.md5()
    num = 0
    parts = []
    with open(file_path, 'rb') as f:
        while 1:
            data = f.read(Bytes)
            if data:
                md5.update(data)
                parts.append(data)
                num = num + 1
            else:
                break
    ret = str(md5.hexdigest())
    return ret, num ,parts


def break_to_parts(file_path):
    parts = []
    with open(file_path, 'rb') as f:
        while 1:
            data = f.read(64000)  # 65536会超
            if data:
                parts.append(data)
            else:
                break
    return parts


class message_Controller(threading.Thread):
    def __init__(self, proxy):
        threading.Thread.__init__(self)
        self.threads = []
        self.proxy = proxy
        self.active = True
        self.destination = []
        self.file_path = {}  # fid---file_path_local
        self.total_data = []
        self.source_name = ""
        self.who_have = False
        self.is_success = False
        self.fid_num = {}
        self.fid_parts_list = {}
        self.close = False
        self.cancel = False

    def __send__(self, data: bytes, dst: (str, int)):
        self.proxy.sendto(data, dst)

    def __recv__(self, timeout=None) -> (bytes, (str, int)):
        return self.proxy.recvfrom(timeout)

    def run(self):
        while self.active:
            msg, frm = self.__recv__()
            temp = '\n'.encode()
            HEAD, client = msg.split(temp)[0].decode(), "(\"%s\", %d)" % frm
            # msg, client = msg.decode(), "(\"%s\", %d)" % frm
            print("PClient收到: " + str(HEAD))
            if HEAD.startswith("Success"):
                self.is_success = True

            elif HEAD.startswith(Cancel_Head):
                self.cancel = True

            elif HEAD.startswith(Close_Head):
                self.close = True

            elif HEAD.startswith(Want_Head):
                file_fid = HEAD.split('-')[1]
                part_id = int(HEAD.split('-')[2])
                t = threading.Thread(target=self.transmit_file(self.file_path[file_fid], frm, file_fid, part_id))
                t.start()
            elif HEAD.startswith(Owner_Head):
                file_detail = HEAD.split(' ')[2]
                fid = file_detail.split('-')[0]
                self.source_name = HEAD.split(' ')[1]
                self.fid_num[fid] = int(HEAD.split(' ')[4])
                part_id = file_detail.split('-')[1]
                num = file_detail.split('-')[2]
                PC = HEAD.split(' ')[3].split('-')[0]
                ip = PC.split(',')[0]
                port = PC.split(',')[1]
                destination = (str(ip), int(port))
                t = threading.Thread(target=self.want_file(destination, fid, part_id))
                t.start()

            elif HEAD.startswith(Transmit_Head):
                self.total_data.append(msg)
                # print("========msg内容=========")
                # print(msg)
                # print("=======================")
                self.who_have = True

    def want_file(self, destination, fid, part_id):
        msg = Want_Head + "-" + fid + "-" + part_id
        self.__send__(msg.encode(), destination)

    def transmit_file(self, file_path, destination, fid, part_id):
        msg = (Transmit_Head + "-" + fid + "-" + str(part_id) + "\n").encode()
        msg = msg + self.fid_parts_list[fid][part_id]
        self.__send__(msg, destination)


class PClient:
    def __init__(self, tracker_addr: (str, int), proxy=None, port=None, upload_rate=0, download_rate=0):
        if proxy:
            self.proxy = proxy
        else:
            self.proxy = Proxy(upload_rate, download_rate, port)  # Do not modify this line!
        self.tracker = tracker_addr
        self.MC = message_Controller(self.proxy)
        self.MC.start()

    def __send__(self, data: bytes, dst: (str, int)):
        self.proxy.sendto(data, dst)

    def __recv__(self, timeout=None) -> (bytes, (str, int)):
        return self.proxy.recvfrom(timeout)

    def register(self, file_path: str):
        """
        注册报文格式如下（REGISTER）：
        报文头：REGISTER-fid-file_name-part_num
        详 细：fid-part_index_0(or 1) -----0代表未结束，1代表结束
        举 例：
         REGISTER-62c97d2c2bdfba2320083770dfb45ec9+test.txt-100（假设分成了100片）
         62c97d2c2bdfba2320083770dfb45ec9-0-0
         62c97d2c2bdfba2320083770dfb45ec9-1-0
         62c97d2c2bdfba2320083770dfb45ec9-2-0
                  ..............
         62c97d2c2bdfba2320083770dfb45ec9-98-0
         62c97d2c2bdfba2320083770dfb45ec9-99-1
        """
        fid, num , lis = hash_fid(file_path)
        self.MC.file_path[fid] = file_path
        if fid not in self.MC.fid_parts_list:
            self.MC.fid_parts_list[fid] = lis
        s = file_path.split('/')
        file_name = s[len(s) - 1]
        message = Register_Head + "-" + fid + "-" + file_name + "-" + str(num) + " "
        for i in range(0, num):
            if i == num - 1:
                temp = fid + "-" + str(i) + "-" + "1"
                message = message + temp
            else:
                temp = fid + "-" + str(i) + "-" + "0" + " "
                message = message + temp
        message = bytes(message, encoding='utf-8')
        self.__send__(message, self.tracker)

        while True:
            if self.MC.is_success:
                self.MC.is_success = False
                break

        return fid

    def download(self, fid) -> bytes:
        message = Query_Head + "-" + fid
        message = bytes(message, encoding='utf-8')
        self.__send__(message, self.tracker)

        data = b''
        time_flag = True
        time_out = time.time()
        while True:
            if time.time() - time_out > 450:
                time_flag = False
                break
            if self.MC.who_have:
                count = 0
                self.MC.who_have = False
                for i in self.MC.total_data:
                    # print("+++++++++" + str(i))
                    temp = '\n'.encode()
                    head = i.split(temp)[0].decode().split("-")
                    this_fid = head[1]
                    if this_fid == fid:
                        count = count + 1
                if count == self.MC.fid_num[fid]:
                    break

        if not time_flag:
            print("~~~~~~~~~~Download again!~~~~~~~~~~~~~")
            self.MC.total_data.clear()
            return self.download(fid)

        parts = []
        for i in self.MC.total_data:
            # print("========="+str(i))
            temp = '\n'.encode()
            head = i.split(temp)[0].decode()
            index = len(head) + 1
            head_content = head.split('-')
            # print("=====" + str(index))
            if head_content[1].startswith(fid):
                parts.append((int(head_content[2]), i[index:]))
        parts.sort(key=lambda k: k[0])
        for i in parts:
            data = data + i[1]

        # print(data.decode() + "~~~~~~~~~~~~~~~~~")

        f_path = '../download_result/'+str(self.proxy.port) + self.MC.source_name
        with open(f_path, 'wb') as f:
            f.write(data)
            f.close()

        self.register(f_path)

        self.MC.total_data.clear()
        self.MC.source_name = ""

        return data

    def cancel(self, fid):
        msg = "CANCEL-" + str(fid)
        msg = bytes(msg, encoding='utf-8')
        self.__send__(msg, self.tracker)
        while True:
            if self.MC.cancel:
                self.MC.cancel = False
                break

    def close(self):
        msg = "CLOSE"
        msg = bytes(msg, encoding='utf-8')
        self.__send__(msg, self.tracker)
        while True:
            if self.MC.close:
                self.MC.close = False
                break
        # time.sleep(2)
        self.proxy.close()


if __name__ == '__main__':
    f1 = open("./download_result/test.txt", "rb")
    data1 = f1.read()
    print(data1)
    # f2 = open("./test_files/bg.png", "rb")
    # data1 = f2.read()
    # print(data1)
