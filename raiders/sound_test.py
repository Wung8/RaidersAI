import pygame, random
pygame.init()
pygame.mixer.init()
pygame.mixer.set_num_channels(32)

sound = pygame.mixer.Sound("Wood_dig3.ogg")
sound2 = pygame.mixer.Sound("output.ogg")

#sound.play()
sound2.play()

pygame.time.wait(2000)
pygame.quit()
