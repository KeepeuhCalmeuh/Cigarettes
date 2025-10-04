import numpy as np
import sounddevice as sd
import time

SAMPLE_RATE = 5000  # Sample rate in Hz
NOTE_DURATION = 0.2  # Duration of each note in seconds
VOLUME = 0.7         # Volume (between 0.0 and 1.0)

def play_notes(melody, duration=NOTE_DURATION, volume=VOLUME, samplerate=SAMPLE_RATE):
    
    """
    Plays a sequence of frequencies (notes).
    A frequency of 0 results in a silence (rest).
    """
    num_samples = int(samplerate * duration)
    t = np.linspace(0., duration, num_samples, endpoint=False)
    
    for frequency in melody:
        if frequency > 0:
            # Generate sine wave for the frequency
            wave = volume * np.sin(2. * np.pi * frequency * t)

            sd.play(wave, samplerate)
            sd.wait() # Wait until the note is completely played
            
        else:
            time.sleep(duration) # Pause for the duration of the rest


def play_incoming_call_sound():
    """Play a sound sequence for an incoming call notification."""
    incoming_call_notification = [700, 700, 700]  # Three short beeps
    play_notes(incoming_call_notification)

def play_message_received_sound():
    """Play a sound sequence for a new message notification."""

    # Actually not usable, it's too annoying like really

    message_received_notification = [900, 1100]  # Rising tone
    play_notes(message_received_notification)