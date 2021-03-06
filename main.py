__author__ = 'thorvald'

from core import Star,Team,Graphics,ViewPort,run_update_tick

from AI import AI

def main():
    [Star(800) for _ in range(100)]
    Graphics(ViewPort(), run_update_tick)
    Team(None, "player")
    Team(AI, "enemy 1")
    Team(AI, "enemy 2")
    Team(AI, "enemy 3")

    Graphics.instance.mainloop()

def main_auto(): #No players on AI. Used for profiling
    [Star(800) for _ in range(100)]
    Graphics(ViewPort(), run_update_tick)
    Team(AI, "player")
    Team(AI, "enemy 1")
    Team(AI, "enemy 2")
    Team(AI, "enemy 3")

    Graphics.instance.mainloop()

if __name__ == "__main__":
    main()