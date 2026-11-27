/* LOCAL (2026-11-27, not from the kit author): the FX2 1.01 counterpart of the A7 IV kit's nrsoff_v1 (spatial noise reduction off). */
/* The camera's own developer switch CamNrOnOff: CAMNRS::job_YC_CalcParam (FX2 0x3b9c14) reads it at 0x3b9e48 as ldrb [arg2, #0x191]; */
/* 1 = take the zeroing path (0x3b9e3c, the stage's enables 0), 0 or 2 = normal, else the "CamNrOnOff = 0x%x" error print. Its only */
/* caller 0x9a832e passes arg2 = r6 = 0x1f431f0 (movw/movt at 0x9a8164; the same function hands r6 + 0x190 to 0x3983f8). So the byte */
/* is 0x1f43381, the second of the four flag bytes at 0x1f43380 (the A7 IV design's SHD, CAMNR, YAP, LIM28 group at 0x1a39188). */
/* Guards: the two code words that tie this address to this firmware (the movw/movt of the base and the reader). RAM only: a cold */
/* boot (battery out 10 s) puts the switch back; Z17 puts it back without one. Not run on any camera, nor is the A7 IV original. */
#define WORDS_DESIGN "nrsoff_fx2_v1"
struct ram_word { u32 address; u8 stock[4]; u8 changed[4]; };
static const struct ram_word ram_words[] = {
    { 0x1f43380, { 0x00, 0x00, 0x00, 0x00 }, { 0x00, 0x01, 0x00, 0x00 } },
};
struct ram_guard { u32 address; u32 len; u8 bytes[16]; };
static const struct ram_guard ram_guards[] = {
    { 0x9a8164, 8, { 0x43, 0xf2, 0xf0, 0x16, 0xc0, 0xf2, 0xf4, 0x16, 0,0,0,0,0,0,0,0 } },
    { 0x3b9e44, 8, { 0xd5, 0xe0, 0x06, 0x99, 0x91, 0xf8, 0x91, 0x11, 0,0,0,0,0,0,0,0 } },
};
