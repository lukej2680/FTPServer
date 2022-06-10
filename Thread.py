# Thread.py
# This is the Thread class for the multithreaded server. Here we define the threads socket, address and state. 
#   The socket is used to recieve and send messages along the control connection
#   The address ID's the connection
#   The state is the current state the thread is in where it responds to commands from the client differently
# On .start() the threads run() method will begin starting by sending a 220 message to the client and then handing all requests from said client. 
# The thread uses a try catch cluase to handle Connection resets or broken pipes and disconnects from the client
# The thread will disonnect if the user quits the program as well. 
# Dependencies;
#   RequestHandler.py


import socket, threading
from RequestHandler import RequestHandler


class NewThread(threading.Thread):
    def __init__(self, socket, address, logfile, modes):
        # Define the socket, address and state for the thread on init
        threading.Thread.__init__(self) 
        self.socket = socket
        self.address = address
        self.logfile = logfile
        self.modes = modes


    def run(self):
        self.logfile.appendLog("New thread created for " + str(self.address))

        # Send successful connection message, begin loop to wait for client response
        self.socket.send("220 Welcome to FTP Server".encode())

        # Create a RequestHandler object
        RequestHandlerObject = RequestHandler(self.socket, self.logfile, self.modes)

        while True:
            try:
                data = self.socket.recv(2048)
                request = data.decode()
                self.logfile.appendLog("Recieved from client" + str(self.address) + ": " + request)

                msg = RequestHandlerObject.handleRequest(request)
                self.logfile.appendLog("Sending to client " + str(self.address) + ": " + msg)
                self.socket.send(msg.encode())
                if (msg == '421 Bye!'): break
            except ConnectionResetError:
                break
            except BrokenPipeError:
                break
            except socket.error:
                self.socket.send('421 Timeout'.encode())
                break

        self.logfile.appendLog("Client " + str(self.address) + ": Disconnected")
        self.socket.close()



