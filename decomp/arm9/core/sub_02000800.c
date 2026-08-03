#include <stdint.h>
/* Confirmed entry mapping; called routines retain neutral names. This is a
 * functional control-flow reconstruction, not claimed original source. */
extern void sub_02000ab0(void);
extern void sub_02000954(uint32_t value, void *end, uint32_t size);
void sub_02000800(void) {
    volatile uint16_t *ipc_sync = (volatile uint16_t *)0x04000208;
    *(volatile uint32_t *)0x04000208 = 0x04000000;
    while (*ipc_sync != 0) { }
    sub_02000ab0();
    /* Instructions after this call establish IRQ/SVC/system stack pointers,
       clear a 0x4000-byte stack/work region, then continue SDK startup. */
}
