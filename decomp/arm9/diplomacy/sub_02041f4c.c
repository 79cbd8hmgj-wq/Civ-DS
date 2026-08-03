#include <stdbool.h>
#include <stdint.h>
/* Confirmed storage shape and direct-write behavior. Network helper names and
 * relationship value names remain neutral pending protocol/runtime evidence. */
extern int32_t g_relationship_state_0219fb54[6][6];
extern int32_t g_network_active_0219fa6c;
extern bool sub_02090460(int32_t civilization);
extern void sub_02089788(int32_t message_id, int32_t a, int32_t b, int32_t value);
extern void sub_02093a4c(void);
void sub_02041f4c(int32_t a, int32_t b, int32_t value, bool propagate) {
    if (g_relationship_state_0219fb54[a][b] == value && value != 0) return;
    if (!g_network_active_0219fa6c || !propagate) {
        g_relationship_state_0219fb54[a][b] = value;
        g_relationship_state_0219fb54[b][a] = value;
        return;
    }
    if (sub_02090460(b) && !sub_02090460(a)) { int32_t swap=a; a=b; b=swap; }
    sub_02089788(38, a, b, value);
    sub_02093a4c();
}
