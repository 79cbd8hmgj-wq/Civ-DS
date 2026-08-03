#include <stdint.h>
/* Presentation-only reconstruction. Array meanings and renderer ABI remain
 * candidates; this routine must not be used as a relationship mutation hook. */
void overlay1_sub_02206610(int32_t civilization_index) {
    /* Clamp and combine several ARM9-resident per-civilization counters.
       Format status rows including peace/war turn counts.
       Submit each formatted row to neutral ARM9 drawing interfaces.
       The exact globals remain unnamed pending mutation/save cross-references. */
    (void)civilization_index;
}
