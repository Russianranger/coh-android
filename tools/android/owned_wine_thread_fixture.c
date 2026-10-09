/* A dead leader with a live worker can retain stdout after pthread_exit(). */
#include <pthread.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static void *keep_output_open(void *unused)
{
    (void)unused;
    for (;;)
        sleep(1);
    return NULL;
}

int main(int argc, char **argv)
{
    pthread_t worker;
    /* The unrelated sentinel must reveal an accidental TERM, not ignore it. */
    int sentinel = argc == 2 && strcmp(argv[1], "--sentinel") == 0;
    if (argc > 2 || (argc == 2 && !sentinel))
        return 4;
    if (signal(SIGTERM, sentinel ? SIG_DFL : SIG_IGN) == SIG_ERR)
        return 1;
    if (pthread_create(&worker, NULL, keep_output_open, NULL) != 0)
        return 2;
    if (puts("worker_ready") < 0 || fflush(stdout) != 0)
        return 3;
    pthread_exit(NULL);
}
