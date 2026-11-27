/* LOCAL (2026-11-27, not from the kit author): 1.5x anamorphic preview on the FX2's rear screen, on top of S16 (lcd32dsq_fx2_v1). */
/* FX2 1.01's menu offers De-Squeeze Display Off / 1.3x / 2.0x. S16 sets code 1 (1.3x), 16:9 picture, to height = width x 20/39 */
/* (1.95:1 for a 3:2 picture). This step makes that same menu entry height = width x 4/9 = 2.25:1, the shape of a 3:2 frame shot */
/* through a 1.5x anamorphic lens. Code (decoded): 0x1fa162 mov.w sb, #d ; 0x1fa166 mov.w sl, #n ; S16's d 39 / n 20 -> d 9 / n 4. */
/* Its stock bytes are S16's applied bytes, so it refuses unless S16 is in place. A17 puts back S16's 1.95:1 (not the camera's stock); */
/* a cold boot puts back everything. Guards: the code around the two immediates, as in the file (S16 does not change them). */
/* Display only: nothing in the recording changes. Not run on any camera. */
#define WORDS_DESIGN "dsq15_fx2_v1"
struct ram_word { u32 address; u8 stock[4]; u8 changed[4]; };
static const struct ram_word ram_words[] = {
    { 0x1fa164, { 0x27, 0x09, 0x4f, 0xf0 }, { 0x09, 0x09, 0x4f, 0xf0 } },
    { 0x1fa168, { 0x14, 0x0a, 0x03, 0xe0 }, { 0x04, 0x0a, 0x03, 0xe0 } },
};
struct ram_guard { u32 address; u32 len; u8 bytes[16]; };
static const struct ram_guard ram_guards[] = {
    { 0x1fa158, 12, { 0x4f, 0xf0, 0x1a, 0x09, 0x4f, 0xf0, 0x0f, 0x0a, 0x08, 0xe0, 0x4f, 0xf0, 0,0,0,0 } },
    { 0x1fa16c, 8, { 0x4f, 0xf0, 0x02, 0x09, 0x4f, 0xf0, 0x01, 0x0a, 0,0,0,0,0,0,0,0 } },
};
