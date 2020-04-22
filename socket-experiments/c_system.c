/* Demonstrates the problem with 'system' command.
 * It's not any faster on C. Sockets are needed.
*/

#define _POSIX_C_SOURCE 200809L

#include <inttypes.h>
#include <math.h>
#include <time.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>

long long current_timestamp()
{
    struct timeval te;
    gettimeofday(&te, NULL);
    long long milliseconds = te.tv_sec * 1000LL + te.tv_usec / 1000;
    // printf("milliseconds: %lld\n", milliseconds);
    return milliseconds;
}

int main(void)
{
    char command[50];
    strcpy(command, "node socket-experiments/js_hello_world.js");
    for (int i = 0; i < 100; i++)
    {
        //printf("C before: %lld\n", current_timestamp());
        system(command);
        //printf("C after-: %lld\n", current_timestamp());
    }
    puts("Hello World! This is a test program.");
    return 0;
}