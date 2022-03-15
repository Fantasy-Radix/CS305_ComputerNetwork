from Proxy import Proxy
from threading import Thread



class Server:
    def __init__(self, upload_rate, download_rate, packet_size=1024, port=10087):
        self.proxy = Proxy(upload_rate, download_rate, port)
        print("Server bind to", self.proxy.port)
        self.packet_size = packet_size

        self.tthread = Thread(target=self.transfer_thread)
        self.active = True

    def __send__(self, data: bytes, dst: (str, int)):
        """
        Do not modify this function!!!
        You must send all your packet by this function!!!
        :param data: The data to be send
        :param dst: The address of the destination
        """
        self.proxy.sendto(data, dst)

    def __recv__(self, timeout=None) -> (bytes, (str, int)):
        """
        Do not modify this function!!!
        You must receive all data from this function!!!
        :param timeout: if its value has been set, it can raise a TimeoutError;
                        else it will keep waiting until receive a packet from others
        :return: a tuple x with packet data in x[0] and the source address(ip, port) in x[1]
        """
        return self.proxy.recvfrom(timeout)

    def start(self):
        self.tthread.start()

    def transfer_thread(self):
        while self.active:
            try:
                msg, frm = self.__recv__(1)
            except Exception:
                continue

            msg = msg.decode()
            print("%s:%d ask for %s" % (frm[0], frm[1], msg))
            with open("../test_files/%s" % msg, 'rb') as f:
                data = f.read()

            packets = [data[i * self.packet_size: (i + 1) * self.packet_size]
                       for i in range(len(data) // self.packet_size + 1)]

            self.__send__(str(len(packets)).encode(), frm)
            print("Total length of %s is %d bytes, %d packets" % (msg, len(data), len(packets)))
            for packet in packets:
                self.__send__(packet, frm)

    def close(self):
        self.active = False


if __name__ == '__main__':
    server = Server(upload_rate=30000, download_rate=1000000, port=10087)
    server.start()
