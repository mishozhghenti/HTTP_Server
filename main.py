import sys
import json
from socket import *
import threading
import time
import datetime
import magic

# final variables
LOG = 'log'
SERVER = 'server'
V_HOST = 'vhost'
IP = 'ip'
PORT = 'port'
DOCUMENT_ROOT = 'documentroot'

MIN_NUM_LISTEN = 1024
KEEP_ALIVE_TIME = 5
KEEP_ALIVE_MAX = 100

CONNECTION = "Connection:"
KEEP_ALIVE = "keep-alive"
HOST = "Host:"
RANGE = "Range:"


def read_configfile(file_name):
    open_file = open(file_name, 'r')
    text = ""
    for x in open_file.read():
        text += x
    return (text)


def read_json_servers(jsonServers, host_dictionary):
    servers = []
    for i in range(len(jsonServers)):
        curr_server = {}
        curr_server[V_HOST] = jsonServers[i][V_HOST]
        curr_server[IP] = jsonServers[i][IP]
        curr_server[PORT] = jsonServers[i][PORT]
        curr_server[DOCUMENT_ROOT] = jsonServers[i][DOCUMENT_ROOT]
        servers.append(curr_server)
        host_dictionary[curr_server[V_HOST]] = curr_server[DOCUMENT_ROOT]
    return (servers)


def isKeepAlive(tokens):
    if (CONNECTION in tokens):
        connection_string_index = tokens.index(CONNECTION)
        keep_alive_index = connection_string_index + 1
        if (keep_alive_index < len(tokens)):
            if (tokens[keep_alive_index] == KEEP_ALIVE):
                return True
    return False


def requestMethod(tokens):
    return tokens[0][0:len(tokens[0])]


def getHOST(tokens):
    host = ""
    const_host = ""
    if ("host:" in tokens):
        const_host = "host:"
    if ("Host:" in tokens):
        const_host = "Host:"

    if (HOST in tokens or "host:" in tokens):
        index = tokens.index(const_host)
        if (index + 1 < len(tokens)):
            host = tokens[index + 1]

    res = host.split(":")
    return res[0]


def readFile(open_file, lower, upper):
    file_text = ""
    file_size = 0
    for x in open_file.read():
        if (file_size >= int(lower) and (upper == -1 or file_size <= int(upper))):
            file_text = file_text + chr(x)
        file_size = file_size + 1

    return file_text, file_size


def getRange(tokens):
    lower = 0
    upper = -1
    hasRangeHeader = False
    if (RANGE in tokens):
        hasRangeHeader = True
        range_request_index = tokens.index(RANGE)
        a = tokens[range_request_index + 1].split("bytes=")
        range_value = a[1]

        range_borders = range_value.split("-")
        lower = range_borders[0]
        if (not (range_borders[1] == "")):
            upper = int(range_borders[1])
    return (lower, upper, hasRangeHeader)


def responseAddHeader(response, header):
    response = response + header
    return response


def get404Error(server_time):
    return str.encode('HTTP/1.1 404 REQUESTED DOMAIN NOT FOUND\r\n' \
                      'Date: {date}\r\n' \
                      'Content-Type: text/html\r\n' \
                      'Accept-Ranges: bytes\r\n' \
                      'Content-Length: 26\r\n' \
                      'Server: mzhgh14@freeuni.edu.ge assignment#1\r\n' \
                      '\r\n' \
                      'REQUESTED DOMAIN NOT FOUND'.format(date=server_time))


def stringToByteArray(string):
    return str.encode(string)


def save_log(log, current_log, host):
    # print(log + host_dictionary[host] + ".log")
    file = open(log + "/" + host_dictionary[host] + ".log", 'a')
    file.write(current_log)
    file.close()


def save_error_log(log, current_log):
    file = open(log + "/error.log", "a")
    file.write(current_log)
    file.close()


def serveRequest(connectionSocket, log):
    while 1:
        try:
            sentence = connectionSocket.recv(1024)
            request_header = sentence.decode('utf-8')

            tokens = request_header.split()
            mime = magic.Magic(mime=True)
            method = requestMethod(tokens)  # GET or HEAD supported
            host = getHOST(tokens)
            keepAlive = isKeepAlive(tokens)
            arguments = tokens[1]
            arguments_token = arguments.split(".")

            request_file_name_path_token = arguments.split("%20")
            path = ""
            for i in range(len(request_file_name_path_token)):
                path = path + request_file_name_path_token[i]
                if (not i == len(request_file_name_path_token) - 1):
                    path = path + " "

            # log

            lower, upper, hasRangeHeader = getRange(tokens)

            #            date = (str(datetime.datetime.today().strftime("[%a %b %d %X %Y]")))
            server_time = datetime.datetime.today().strftime("%a %b %d %X %Y")

            log_text_module = "[{DATE}] {IP} {HOST} {ARG} {STATUS_CODE} {BYTES} \"{AGENT}\"\n"
            agent = ""
            user_agent_index = tokens.index("User-Agent:")

            for i in range(user_agent_index + 1, len(tokens)):
                if (not tokens[i].endswith(":")):
                    agent += tokens[i]
                    agent += " "
                else:
                    agent = agent[0:len(agent) - 1]
                    break
            ip, port = connectionSocket.getpeername()

            if (not host in host_dictionary):
                # print("host is not in my dictionary", host)
                log_text = log_text_module.format(DATE=server_time, IP=ip, HOST=host, ARG=path, STATUS_CODE="404",
                                                  BYTES="26", AGENT=agent)
                save_error_log(log, log_text)
                connectionSocket.send(get404Error(server_time))
                connectionSocket.close()
            else:

                try:
                    file_text, full_file_size = readFile(open(host_dictionary[host] + path, 'rb'), lower, upper)
                    status = ""
                    response = ""


                    control=False
                    if(hasRangeHeader):
                        bottom=int(lower)
                        UP=int(upper)
                        if(not UP==-1):
                            if(bottom>UP):
                                control=True
                                response = response + ("HTTP/1.1 416 Range Not Satisfiable\r\n")
                                status="416"


                    if(not control):
                        if (hasRangeHeader):
                            response = response + ("HTTP/1.1 206 Partial Content\r\n")
                            status = "206"
                        else:
                            response = response + ("HTTP/1.1 200 OK\r\n")
                            status = "200"

                    response = response + ("Date: " + str(server_time) + "\r\n")
                    response = response + ("Server: mzhgh14 assignment#1\r\n")
                    response = response + ("ETag: \"45b6-834-49130cc1182c0\"\r\n")

                    if (keepAlive):
                        response = response + ("Connection: keep-alive\r\n")
                        response = response + (
                            "keep-alive: timeout=" + str(KEEP_ALIVE_TIME) + ", max=" + str(KEEP_ALIVE_MAX) + "\r\n")

                    if (hasRangeHeader):
                        range_upper = ""
                        if (upper == -1):
                            range_upper = str(full_file_size - 1)
                        else:
                            range_upper = str(upper)
                        response = response + (
                            "Content-Range: bytes " + str(lower) + "-" + range_upper + "/" + str(
                                full_file_size) + "\r\n")

                    response = response + ("Content-Length: " + str(len(file_text)) + "\r\n")
                    response = response + ("Accept-Ranges: bytes\r\n")
                    response = response + ("Content-Type: " + mime.from_file(host_dictionary[host] + path) + "\r\n")
                    response = response + ("\r\n")

                    ################################################
                    #            body                              #
                    ################################################


                    connectionSocket.send(stringToByteArray(response))
                    #   log_text_module = "{DATE} {IP} {HOST} {ARG} {STATUS_CODE} {BYTES}\"{AGENT}\""


                    log_text = log_text_module.format(DATE=server_time, IP=ip, HOST=host, ARG=path, STATUS_CODE=status,
                                                      BYTES=str(len(file_text)), AGENT=agent)

                    save_log(log, log_text, host)

                    if (method == "GET"):
                        if (upper == -1):
                            connectionSocket.sendfile(open(host_dictionary[host] + path, 'rb'), int(lower))
                        else:
                            connectionSocket.sendfile(open(host_dictionary[host] + path, 'rb'), int(lower), int(upper))
                    if (keepAlive):
                        connectionSocket.settimeout(5)
                    else:
                        connectionSocket.close()
                except:

                    log_text = log_text_module.format(DATE=server_time, IP=ip, HOST=host, ARG=path, STATUS_CODE="404",
                                                      BYTES="26", AGENT=agent)
                    save_log(log, log_text, host)

                    connectionSocket.send(get404Error(server_time))
                    if (keepAlive):
                        connectionSocket.settimeout(5)
                    else:
                        connectionSocket.close()
        except:
            connectionSocket.close()
            break


def start_server(server, log):
    try:
        serverPort = server[PORT]
        serverSocket = socket(AF_INET, SOCK_STREAM)
        serverSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        serverSocket.bind((server[IP], serverPort))
        serverSocket.listen(MIN_NUM_LISTEN)
    except:
        # port/ip is already used/cant started
        return

    while 1:
        connectionSocket, addr = serverSocket.accept()
        current_request = threading.Thread(target=serveRequest, args=(connectionSocket, log))
        current_request.start()


def create_log_files(log, host_dictionary):
    for key in (host_dictionary):
        current_path = log + "/" + host_dictionary[key] + ".log"
        file = open(current_path, 'wb')
        file.close()
    error_log = open(log + "/error.log", 'wb')
    error_log.close()


config_path = "config.json"

jsonFile = read_configfile(config_path)
jsonData = json.loads(jsonFile)

log = jsonData[LOG]
host_dictionary = {}
servers = read_json_servers(jsonData[SERVER], host_dictionary)
create_log_files(log, host_dictionary)

threads = []
for i in range(len(servers)):
    t = threading.Thread(target=start_server, args=(servers[i], log))
    threads.append(t)
    t.start()

for i in range(len(threads)):
    threads[i].join()
