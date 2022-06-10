# FtpServer.py
# This is the main server program for the ftp server
# Dependencies;
#   Thread.py


# import required modules
import socket, sys
from Thread import NewThread
import Log


modes = {}

# Check length of arguments for required arguments, error message if incorrect
if (len(sys.argv) < 2):
    print("Missing Arguments")
    print("FtpServer.py <log> <port>")
    exit(1)
logfile = sys.argv[1]
try:
    port = int(sys.argv[2])
except:
    print("Port number must be number.")
    exit(1)

# Build the socket
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Use to avoid the 'Address already in use' error and allow multiple connections
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
# Bind to the localhost and port
server.bind(('', port))

log_file = Log.LogFile(logfile)
log_file.openLog()
log_file.appendLog("Server accepting connections")

# Read the configuration file
try:
    # Hard coded to a location on my computer. Change it for testing purposes
    with open('ftpserverd.conf') as f:
        lines = f.readlines()
        for line in lines:
            l = line.replace(" ", "")
            if (l[0] != '#'):
                a, b = l.split('=')
                b = b.replace('\n', '')
                if (a == 'port_mode'):
                    modes.update({'PORT':b})
                    modes.update({'EPRT':b})
                elif (a == 'pasv_mode'):
                    modes.update({'PASV':b})
                    modes.update({'EPSV':b})
except:
    # If conf is not read properly or not configured properly then defualts
    modes.update({'PORT':'NO'})
    modes.update({'EPRT':'NO'})
    modes.update({'EPSV':'YES'})
    modes.update({'PASV':'YES'})

while True:
    # Listen for a single connection
    server.listen(1)
    # Accept that connection grabbing the socket object and address
    client_sock, client_address = server.accept()
    # Log connection
    log_file.appendLog("New connection from " + str(client_address))
    # Set client timeout
    client_sock.settimeout(60)
    # Create a new Thread object
    newthread = NewThread(client_sock, client_address, log_file, modes)
    # Start the Thread
    newthread.start()
server.close()
