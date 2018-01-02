
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <errno.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/types.h>


/* maximum datagram socket sendto() size: 2**16 - 1 - 8 - 20 */
#define MAX_PKT_SIZE 65507

#define SOCKADDR_SZ sizeof(struct sockaddr_in)


int socket_udp(char* addr, uint16_t port) {

    /* create datagram socket */
    int optval = 1;
    int fd = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &optval, sizeof(int));

    /* create socket address  */
    struct sockaddr_in sockaddr;
    memset((void *) &sockaddr, 0, SOCKADDR_SZ);
    inet_aton(addr, &sockaddr.sin_addr);
    sockaddr.sin_port = htons(port);
    sockaddr.sin_family = AF_INET;

    /* attempt to bind socket to port */
    if (bind(fd, (struct sockaddr *) &sockaddr, SOCKADDR_SZ) < 0) {
        perror("bind failed");
        return 0;
    }

    return fd;
}


void sendto_all(int fd, void* data, uint32_t len, char* haddr,
                uint16_t hport) {

    char *buf = (char *) data;
    uint32_t pktsz = MAX_PKT_SIZE;

    /* compute number of packets required to send entire buffer */
    int npkts = len / pktsz;
    if (len % pktsz > 0) {
        npkts++;
    }

    /* create host address  */
    struct sockaddr_in hostaddr;
    memset((void *) &hostaddr, 0, SOCKADDR_SZ);
    inet_aton(haddr, &hostaddr.sin_addr);
    hostaddr.sin_port = htons(hport);
    hostaddr.sin_family = AF_INET;

    /* send all data */
    for (int i = 0; i < npkts; i++) {
        pktsz = (pktsz < len) ? pktsz : len;
        sendto(fd, (void *) buf, pktsz, 0, (struct sockaddr *) &hostaddr,
               SOCKADDR_SZ);
        len -= pktsz;
        buf += pktsz;
    }

    /* empty packet denotes end of stream */
    sendto(fd, (void *) buf, 0, 0, (struct sockaddr *) &hostaddr,
           SOCKADDR_SZ);
}


void socket_close(int fd) {

    close(fd);
}
