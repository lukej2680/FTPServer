# RequestHandler.py
# This is the Request handler class
# Each thread starts a new request handler instance and passs its client sock to the instance. 
# The request handler keeps a list of all accepted commands and on init reads the creds.txt file to load the accepted credentials
# The class also contains a data_socket if the client starts a data transfer.  
# The handleRequest method is the main public method which utilizes the private _requestParser method to parse the request and send back the code and data which handleRequest uses to formulate a response to the client.
# handleRequest is also responsible for changing the threads control_socket state


import socket, os, subprocess
from requests import get


class RequestHandler():
    # Accepted commands, accepted users are built into a library in user:password pairs, user for password lookup, control socket initilized on init, data socket created if needed
    accepted_commands = ['USER', 'PASS', 'CWD', 'CDUP', 'QUIT', 'PASV', 'EPSV', 'PORT', 'EPRT',
    'RETR', 'STOR', 'PWD', 'LIST']
    blocked_extensions = ['exe', 'sh', 'bash', 'py']
    accepted_users = {}
    user = ''
    control_socket = None
    data_socket = None

    def __init__(self, control_socket, logfile, modes):
        # Set control socket
        self.control_socket = control_socket
        self.logfile = logfile
        self.modes = modes
        self.state = 'init'
        # Populate the accepted_users using the _readCreds() method
        self._readCreds()

    def handleRequest(self, req):
        # Parse request
        cmd, data = self._requestParser(req)

        # Check for blocked modes
        if (cmd in self.modes and self.modes[cmd] != 'YES'):
            return '500 This command is being blocked by server.\n Try alternate connection mode.'

        # Send invalid command if user enters unrecognized command
        if (cmd == 'invalid'):
            return '502 Invalid command'
        # Send 501 if missing a parameter (USER with no username)
        if (cmd == '501'):
            return '501 Missing Parameter'
        if (cmd == 'QUIT'):
            # Tear down data connection if one was established
            # Send 421 
            if self.data_socket: self.data_socket.close()
            return '421 Bye!'

        # This is the Initialize state. 
        # Command(s) USER - Sends to Authorization state
        # Command(s) PASS, CWD, CDUP, PASV, EPSV, PORT, EPRT, RETR, STOR, PWD, LIST - Send to Initialize state
        if (self.state == 'init'):
            #print(self.state.state)
            # Store the user variable as the user inputted
            if (cmd == 'USER'):
                self.user = data
                self.state = 'auth'
                return '331 User name okay, need password'
            else:
                return '530 Not logged in'

        # This is the Authorization state
        # Command(s) PASS(successful) - Sends to Accepting Commands state
        # Command(s) USER, PASS(unsuccessful), CWD, CDUP, PASV, EPSV, PORT, EPRT, RETR, STOR, PWD, LIST - Send to Initialize state
        elif (self.state == 'auth'):
            #print(self.state)
            # Authenticate the user passed in previous command
            if (cmd == 'PASS'):

                if (self.user in self.accepted_users and self.accepted_users[self.user] == data):
                    self.state = 'cmd'
                    return '230 Logged in as ' + self.user
                else:
                    self.state = 'init'
                    return '430 Invalid username or password'
            else:
                self.state = 'init'
                return '530 Not logged in'
        
        # This is the Accepting Commands state. 
        # Command(s) PORT, EPRT, PASV, EPSV - Sends to File Transfer state
        # Command(s) CWD, CDUP, RETR, STOR, PWD, LIST - Send to Accepting Commands state
        # Command(s) PASS - Sends to the Authorization state
        elif (self.state == 'cmd'):
            #print(self.state)
            # PORT accepts a properly formatted PORT command and creates a data_socket on the specified ip/port returning a 225 and moving to auth state
            if (cmd == 'PORT'):
                try:
                    h1, h2, h3, h4, p1, p2 = data.replace('(', '').replace(')', '').split(',')
                    p1 = int(p1)
                    p2 = int(p2)
                except:
                    return '501 Syntax error in parameters or arguments\nPORT (h1,h2,h3,h4,p1,p2)'

                ip = '.'.join([h1, h2, h3, h4])
                port = ((p1 * 256) + p2)

                self.data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.data_socket.connect((ip, port))
                
                self.state = 'tran'
                return '225 Data connection open; no transfer in progress'

            # EPRT or Extended PORT
            # After parsing a properly formatted EPRT command establish a ipv4 or ipv6 connection
            elif (cmd == 'EPRT'):
                try:
                    v, ip, port = data.split('|')
                except:
                    return '501 Syntax error in parameters or arguments' 

                if (v == '1'):
                    self.data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.data_socket.connect((ip, port))

                    self.state = 'tran'
                    return '225 Data connection open; no transfer in progress'
                else:
                    self.data_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                    self.data_socket.connect((ip, port, 0, 0))

                    self.state = 'tran'
                    return '225 Data connection open; no transfer in progress'

            # Set up a listener at specified port and send the client the servers local ip and listning port
            elif (cmd == 'PASV'):
                ip = get('https://api.ipify.org').content.decode('utf8')
                h1, h2, h3, h4 = ip.split('.')

                p1, p2 = 34, 43

                self.data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.data_socket.bind(('', (p1 * 256) + p2))

                msg = '227 Entering Passive Mode (' + h1 + ',' + h2 + ',' + h3 + ',' + h4 + ',' + str(p1) + ',' + str(p2) + ').'

                self.state = 'tran'

                return msg

            # EPSV or Extended PASV assumes the ip to be the same as the control channel and connects on the port sent by the client
            elif (cmd == 'EPSV'):
                try:
                    port = int(data)
                    ip = self.control_socket.gethostbyname(self.control_socket.gethostname())
                except:
                    return '501 Syntax error in parameters or arguments'

                self.data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.data_socket.connect((ip, port))

                self.state = 'tran'
                return '225 Data connection open; no transfer in progress'

            # CWD Changes the working directory and returns 400 codes if any errors
            elif (cmd == 'CWD'):
                try:
                    os.chdir(data)
                    return '200 Directory changed successfuly'
                except FileNotFoundError:
                    return '400 Directory does not exist'
                except NotADirectoryError:
                    return '400 Is not a Directory'
                except PermissionError:
                    return '400 Not authorized'

            # CDUP changes to parent directory and sends 400 codes if failed
            elif (cmd == 'CDUP'):
                try:
                    os.chdir('..')
                    return '200 Directory changed successfuly'
                except:
                    return '400 Command failed'
            
            # Not availible in this state
            elif (cmd == 'RETR'):
                return '425 Data connection not open'
            
            # Not availible in this state 
            elif (cmd == 'STOR'):
                return '425 Data connection not open'

            # Return the current directory
            elif (cmd == 'PWD'):
                return '212 ' + os.getcwd()

            # Not availible in this state
            elif (cmd == 'LIST'):
                return '425 Data connection not open'

            # Sign in as a new user and send back auth 
            elif (cmd == 'PASS'):
                self.user = data
                self.state = 'auth'
                return '331 User name okay, need password'
        
        # This is the File Transfer state. 
        # Command(s) USER, PASS, CWD, CDUP, PASV, EPSV, PORT, EPRT, RETR((un)successful), STOR((un)successful), PWD, LIST((un)successful) - Send to Accepting Commands state
        elif (self.state == 'tran'):
            # THe list command uses a subporocess to call ls -l and send the results over the data socket. Breaking the socket after transfer
            if (cmd == 'LIST'):
                dir_list = subprocess.check_output(['ls', '-l'])

                self.logfile.appendLog("Sending to client " + str(self.control_socket.getsockname()) + ": 150 Directory contents to follow")
                self.control_socket.send('150 Directory contents to follow'.encode())
                
                try:
                    self.data_socket.sendall(dir_list)
                    self.data_socket.close()
                except OSError:
                    self.state = 'cmd'
                    return '500 Socket is not connected'

                self.state = 'cmd'
                return '226 Directory send OK'

            # The STOR command opens a new file on the server with the specified filename and writes to the file data recieved on the data channel before tearing down the connection
            elif (cmd == 'STOR'):
                try:
                    if (data.split('.')[-1] not in self.blocked_extensions): # Check filename for blocked file extension
                        f = open(data, "wb")

                        self.logfile.appendLog("Sending to client " + str(self.control_socket.getsockname()) + ": 150 Directory contents to follow")
                        self.control_socket.send('150 Opening BINARY mode data connecton'.encode())

                        while True:
                            d = self.data_socket.recv(4098)
                            f.write(d.decode())
                            if not d:
                                break
                        f.close()

                        self.data_socket.close()
                        self.state = 'cmd'
                        return('226 Transfer complete.')
                    else:
                        return('500 Blocked File Extension') # Send error message to client
                except:
                    self.state = 'cmd'
                    return('500 Error')

            # The RETR command opens a local file and sends the data over the data channel before tearing the channel down. 
            elif (cmd == 'RETR'):
                try:
                    f = open(data, 'rb')

                    self.logfile.appendLog("Sending to client " + str(self.control_socket.getsockname()) + ": 150 Directory contents to follow")
                    self.control_socket.send('150 Opening BINARY mode data connection'.encode())

                    while True:
                        d = f.read(4098)
                        self.data_socket.send(d.encode())
                        if not d:
                            break
                    f.close()
                    self.data_socket.close()

                    self.state = 'cmd'
                    return '226 Transfer complete.'
                except:
                    self.state = 'cmd'
                    return '500 Invalid file name'

            else:
                return '500 Command not implemented.'
    
        return cmd

    def _requestParser(self, req):
        if (not req or req.split()[0] not in self.accepted_commands):
            return 'invalid', None

        cmd = req.split()[0]

        if (cmd in ['USER', 'PASS', 'CWD', 'PORT', 'EPRT', 'RETR', 'STOR']):
            try:
                data = req.split()[1]
                return cmd, data
            except IndexError:
                return '501', None
        else:
            return cmd, None
    
    def _readCreds(self):
        try:
            with open('creds.txt') as f:
                lines = f.readlines()
                for line in lines:
                    line = line.replace('\n', '')
                    user, password = line.split(':')
                    self.accepted_users.update({user:password})
        except IOError:
            self.accepted_users.update({'anonymous':'anonymous'})
