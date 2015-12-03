def from_no_yes_to_DT_Bool(x):
    # no - yes translated to 0 - 1
    if x == "no":
        return 0
    else:
        return 1

