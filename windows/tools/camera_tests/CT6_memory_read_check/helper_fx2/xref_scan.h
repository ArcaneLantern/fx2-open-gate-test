/* xref_scan.h: find who uses a few known coprocessor addresses, in one 4 KB page of Thumb-2 code (LOCAL, 2026-11-28).
 * Pure: no I/O, no allocation. Included by fx2read.c for the xref dump build (-DDUMP=2), and by a host test.
 *   - calls: a Thumb-2 BL or B.W (encoding T4) at a halfword whose target is one of `calls`
 *   - literals: an aligned 32-bit word equal to one of `lits`
 * A BL/B.W pair that crosses the page end is not seen; the targets here are function starts, not page ends. */
#ifndef XREF_SCAN_H
#define XREF_SCAN_H

typedef void (*xref_hit)(int kind, unsigned int target, unsigned int at);   /* kind 0: call, 1: literal */

static void xref_page(const unsigned char *p, unsigned int base, const unsigned int *calls, unsigned int ncalls,
                      const unsigned int *lits, unsigned int nlits, xref_hit hit)
{
    for (unsigned int o = 0; o + 4 <= 4096; o += 2) {
        unsigned int h1 = p[o] | (unsigned int)p[o + 1] << 8, h2 = p[o + 2] | (unsigned int)p[o + 3] << 8;
        if ((h1 & 0xF800) == 0xF000 && ((h2 & 0xD000) == 0xD000 || (h2 & 0xD000) == 0x9000)) {   /* BL / B.W T4 */
            unsigned int s = (h1 >> 10) & 1, j1 = (h2 >> 13) & 1, j2 = (h2 >> 11) & 1;
            unsigned int i1 = !(j1 ^ s), i2 = !(j2 ^ s);
            unsigned int imm = s << 24 | i1 << 23 | i2 << 22 | (h1 & 0x3FF) << 12 | (h2 & 0x7FF) << 1;
            int off = (int)(imm << 7) >> 7;                                               /* sign-extend 25 bits */
            unsigned int t = base + o + 4 + (unsigned int)off;
            for (unsigned int k = 0; k < ncalls; k++) if (t == calls[k]) hit(0, t, base + o);
        }
        if (!(o & 3)) {
            unsigned int w = h1 | h2 << 16;
            for (unsigned int k = 0; k < nlits; k++) if (w == lits[k]) hit(1, w, base + o);
        }
    }
}
#endif
