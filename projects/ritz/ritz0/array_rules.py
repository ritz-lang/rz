"""What an array store may not do (LANGUAGE_SPEC §3.3, LARB ruling R5, AGAST #2343).

The wording is shared: ritz1 prints the same string (ref_check.ritz), and
ritz0/test_array_store_rule.py holds all three compilers to it.
"""

# A non-literal `[N]T1` where a `[N]T2` goes. A literal takes the slot's element
# type; anything else has one already, and converting it is a loop you write.
ELEMENT_MISMATCH = "an array only fits a slot of the same element type: write a loop to convert it"
