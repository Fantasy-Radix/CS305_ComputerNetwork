from Proxy import Proxy
from threading import Thread

server_address = ("127.0.0.1", 10087)


class Client:
    def __init__(self, name, download_rate):
        self.proxy = Proxy(upload_rate=0, download_rate=download_rate)
        self.name = name
        print("%s(%d) create" % (name, download_rate))

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

    def download(self, file: str):

        self.__send__(file.encode(), server_address)
        print("%s ask for %s" % (self.name, file))

        msg, frm = self.proxy.recvfrom()

        data = b""
        for idx in range(int(msg.decode())):
            msg, frm = self.__recv__()
            data += msg
            print("%s receive %d" % (self.name, idx))

        with open("../test_files/%s" % file, "rb") as f:
            if f.read() == data:
                print("[%s] Finish!" % self.name)
            else:
                print("Something wrong!")


def client_download(client):
    client.download("../test_files/bg.png")


if __name__ == '__main__':
    # the download rate of different clients
    rates = [50000, 30000, 10000]
    # rates = [3000]
    threads = []

    for i, rate in enumerate(rates):
        c = Client("c%d" % (i + 1), rate)
        threads.append(Thread(target=client_download, args=[c]))

    for thread in threads:
        thread.start()
