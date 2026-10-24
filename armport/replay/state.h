#pragma once
void armportReplayStateInit(void);
unsigned armportReplayStateSave(const char *directory, unsigned index, char digest[65]);
