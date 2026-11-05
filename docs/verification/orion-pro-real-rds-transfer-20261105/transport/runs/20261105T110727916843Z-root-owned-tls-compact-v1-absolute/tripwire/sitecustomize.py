import socket,subprocess
def deny(*a,**k): raise RuntimeError('UNEXPECTED_EXTERNAL_OPERATION')
socket.socket.connect=deny
socket.getaddrinfo=deny
subprocess.Popen=deny
