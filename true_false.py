# define `True` and `False` if necessary
try:
    # make module-global copies
    True = True
    False = False
except NameError:
    True, False = (1 == 1), (1 == 0)

