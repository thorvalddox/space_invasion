__author__ = 'thorvald'

import random



def generate_name():
    consonants = tuple("bcdfghjklmnprstvwxz") + ("qu",)
    vowels = tuple("aeiou")
    beg_before_r = tuple(l+"r" for l in "bcdfgkptvw")
    beg_after_s = tuple("s" + l for l in "chlpt") + ("str","scr")
    end_comb = tuple("dfgklmnprstxyz") + ("ck","st")
    start = ("",) + consonants + beg_before_r + beg_after_s
    mid = consonants
    vow = vowels + ("ai","ee","ou","oi")
    end = end_comb
    vow_end = vowels + ("ey","y","an","us","um")
    return "".join(gen_from_struct(start,vow,mid,vow,mid,vow_end)).title()

def gen_from_struct(*struct):
    for s in struct:
        yield random.choice(s)