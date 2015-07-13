__author__ = 'thorvald'


import cProfile
from main import main

if __name__=="__main__":
    cProfile.run("main()","profile")