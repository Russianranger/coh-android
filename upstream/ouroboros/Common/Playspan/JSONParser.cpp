#include <utilitieslib/stdtypes.h>
#include "JSONParser.h"
#include <utilitieslib/utils/SuperAssert.h>

bool yajl_get_string(yajl_val parent, const char ** path, const char ** value) {
    yajl_val val = yajl_tree_get(parent, path, yajl_t_string);

    if (!devassert(YAJL_IS_STRING(val)))
        return false;

    *value = YAJL_GET_STRING(val);
    return true;
}

bool yajl_get_int(yajl_val parent, const char ** path, int * value) {
    yajl_val val = yajl_tree_get(parent, path, yajl_t_number);

    if (!devassert(YAJL_IS_INTEGER(val)))
        return false;

    *value = YAJL_GET_INTEGER(val);
    return true;
}

bool yajl_get_string_as_int(yajl_val parent, const char ** path, int * value) {
    const char * str_value;
    if (!yajl_get_string(parent, path, &str_value))
        return false;

    char * end = NULL;
    *value = strtol(str_value, &end, 10);
    if (!devassert(end && !*end))
        return false;

    return true;
}

yajl_val parse_json(void * data, size_t size) {
    static char method[64];

    yajl_val tree = yajl_tree_parse(reinterpret_cast<char*>(data), NULL, 0);
    if (!devassertmsg(tree, "Could not parse the JSON:\n%s", tree))
        return NULL;

    return tree;
}