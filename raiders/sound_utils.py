import pygame
import random
import os

pygame.mixer.init()
pygame.mixer.set_num_channels(32)  # allow many sounds

assets_folder = "assets/sounds"
sound_files = [f for f in os.listdir(assets_folder) if f.endswith((".ogg"))]
SOUNDS = {}
SOUNDS_TO_IDX = {}
IDX_TO_SOUND = {}
idx = 0
for file in sound_files:
    f = file
    file = file.split("/")[-1].split(".")[0]
    n = 0
    for n in range(len(file)):
        if file[n].isdigit():
            break
    
    if not file[n].isdigit():
        file = file + "0"
        n += 1
    sound, num = file[:n], file[n:]
    if sound not in SOUNDS:
        SOUNDS[sound] = []
        SOUNDS_TO_IDX[sound] = idx
        IDX_TO_SOUND[idx] = sound
        idx += 1
    SOUNDS[sound].append(pygame.mixer.Sound(os.path.join(assets_folder, f)))

class SoundUtils:

    @staticmethod
    def encodeSoundID(sound):
        return SOUNDS_TO_IDX[sound]

    @staticmethod
    def decodeSoundID(sound_id):
        sound = IDX_TO_SOUND[sound_id]
        return random.choice(SOUNDS[sound])

    @staticmethod
    def playSound(sound_id, dist, scale):
        sound = SoundUtils.decodeSoundID(sound_id)
        channel = sound.play()
        if channel:  # if a free channel was available
            volume = scale * max(0, min(1, 1 - 0.5*dist/300))
            channel.set_volume(volume)