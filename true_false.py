"""
true_false.py - define `True` and `False` if necessary
"""

try:
    # make module-global copies
    True = True
    False = False
except NameError:
    True = (1 == 1)
    False = (1 == 0)

