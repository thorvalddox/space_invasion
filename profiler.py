__author__ = 'thorvald'


import cProfile,os
from main import main_auto as main

if __name__=="__main__":
    cProfile.run("main()","profile")
    os.system("gprof2dot profile -f pstats > profile.dot")