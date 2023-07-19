#!/usr/bin/env python3

import keyboard
import os
import subprocess

from omxplayer.player import OMXPlayer
from time import sleep

class GaplessPlayer:

    PLAYLIST_FILE = "gapless-playlist.txt"
    VIDEO_INDEX_FILE = "video-index.txt"

    def __init__(self, video_folder):

        # Player used for next
        self.player_A = None
        self.player_B = None
        # Player used for previous
        self.player_C = None
        self.player_D = None
        self.current_player = None
        self.next_player = None
        self.previous_player = None
        self.current_video_index = None
        self.next_video_index = None
        self.previous_video_index = None
        self.previousPerformed = False
        self.ready_for_next_previous = True
        self.screen_disabled = False

        # Needed to init omxplayer dbus
        subprocess.call(['omxplayer'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Needed to access omxplayer dbus without X11 env
        self.set_omxplayer_env_vars()

        self.video_files = self.find_mp4_files(video_folder)

        # Check if the output file exists
        if os.path.exists(GaplessPlayer.PLAYLIST_FILE):
            with open(GaplessPlayer.PLAYLIST_FILE, 'r') as f:
                mp4_files = f.read().splitlines()
        else:
            mp4_files = self.find_mp4_files(video_folder)
            with open(GaplessPlayer.PLAYLIST_FILE, 'w') as f:
                f.write('\n'.join(mp4_files))

    def find_mp4_files(self, folder):
        mp4_files = []

        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.endswith(".mp4"):
                    mp4_files.append(os.path.join(root, file))

        return sorted(mp4_files)

    def save_video_index(self, index):
        with open(GaplessPlayer.VIDEO_INDEX_FILE, "w") as file:
            file.write(str(index))

    def load_video_index(self):
        try:
            with open(GaplessPlayer.VIDEO_INDEX_FILE, "r") as file:
                index = int(file.read())
                return index
        except FileNotFoundError:
            # Return a default index or handle the case when the file doesn't exist
            return 0

    def set_omxplayer_env_vars(self):
        omxplayer_dbus_addr = "/tmp/omxplayerdbus.{}".format(os.environ.get('USER', 'root'))
        omxplayer_dbus_pid = "/tmp/omxplayerdbus.{}.pid".format(os.environ.get('USER', 'root'))

        with open(omxplayer_dbus_addr, 'r') as addr_file:
            dbus_address = addr_file.read().strip()
            os.environ['DBUS_SESSION_BUS_ADDRESS'] = dbus_address
            print("dbus_address : ", dbus_address)

        with open(omxplayer_dbus_pid, 'r') as pid_file:
            dbus_pid = pid_file.read().strip()
            os.environ['DBUS_SESSION_BUS_PID'] = dbus_pid
            print("dbus_pid : ", dbus_pid)

    def defineNextPlayer(self):
        next_video = self.video_files[self.next_video_index]
        print("Preparing next video : " +  str(self.next_video_index) + " - " + next_video)
        # Determine the next player
        if self.current_player == self.player_A:
            print("Current player is A, preparing B")
            if (self.player_B is not None):
                self.player_B.quit()
            # Since OmxPlayer sucks ass and cannot be started while on mute, we have to set the volume
            # to a stupidly high value (10000) so that it will overflow and start the player in a muted state.
            # Thus, passing --vol 100000 argument.
            self.player_B = OMXPlayer(next_video,
                args=['--layer', 0, '--vol', 100000],
                dbus_name='org.mpris.MediaPlayer2.omxplayerB')
            self.player_B.playerIdentifier = "Player B - " + next_video
            self.player_B.dbus_name = "org.mpris.MediaPlayer2.omxplayerB"
            self.next_player = self.player_B
        elif self.current_player == self.player_B:
            print("Current player is B, preparing A ")
            if (self.player_A is not None):
                self.player_A.quit()
            # Since OmxPlayer sucks ass and cannot be started while on mute, we have to set the volume
            # to a stupidly high value (10000) so that it will overflow and start the player in a muted state.
            # Thus, passing --vol 100000 argument.
            self.player_A = OMXPlayer(next_video,
                args=['--layer', 0, '--vol', 100000],
                dbus_name='org.mpris.MediaPlayer2.omxplayerA')
            self.player_A.dbus_name = "org.mpris.MediaPlayer2.omxplayerA"
            self.player_A.playerIdentifier = "Player A - " + next_video
            self.next_player = self.player_A
        # If we were on previous player, restart on player A
        else:
            print("Current player is a previous-player, preparing A")
            if (self.player_A is not None):
                self.player_A.quit()
            if (self.player_B is not None):
                self.player_B.quit()
            # Since OmxPlayer sucks ass and cannot be started while on mute, we have to set the volume
            # to a stupidly high value (10000) so that it will overflow and start the player in a muted state.
            # Thus, passing --vol 100000 argument.
            self.player_A = OMXPlayer(next_video,
                args=['--layer', 0, '--vol', 100000],
                dbus_name='org.mpris.MediaPlayer2.omxplayerA')
            self.player_A.dbus_name = "org.mpris.MediaPlayer2.omxplayerA"
            self.player_A.playerIdentifier = "Player A - " + next_video
            self.next_player = self.player_A

    def definePreviousPlayer(self):
        previous_video = self.video_files[self.previous_video_index]
        print("Preparing previous video : " +  str(self.previous_video_index) + " - " + previous_video)

         # Determine the previous player
        if self.current_player == self.player_C:
            print("Current player is C, preparing D")
            if (self.player_D is not None):
                self.player_D.quit()
            # Since OmxPlayer sucks ass and cannot be started while on mute, we have to set the volume
            # to a stupidly high value (10000) so that it will overflow and start the player in a muted state.
            # Thus, passing --vol 100000 argument.
            self.player_D = OMXPlayer(previous_video,
                args=['--layer', 0, '--vol', 100000],
                dbus_name='org.mpris.MediaPlayer2.omxplayerD')
            self.player_D.playerIdentifier = "Player D - " + previous_video
            self.player_D.dbus_name = "org.mpris.MediaPlayer2.omxplayerD"
            self.previous_player = self.player_D
        elif self.current_player == self.player_D:
            print("Current player is D, preparing C")
            if (self.player_C is not None):
                self.player_C.quit()
            # Since OmxPlayer sucks ass and cannot be started while on mute, we have to set the volume
            # to a stupidly high value (10000) so that it will overflow and start the player in a muted state.
            # Thus, passing --vol 100000 argument.
            self.player_C = OMXPlayer(previous_video,
                args=['--layer', 0, '--vol', 100000],
                dbus_name='org.mpris.MediaPlayer2.omxplayerC')
            self.player_C.dbus_name = "org.mpris.MediaPlayer2.omxplayerC"
            self.player_C.playerIdentifier = "Player C - " + previous_video
            self.previous_player = self.player_C
        # If we were on next player, restart on player C
        else:
            print("Current player is a next-player, preparing C")
            if (self.player_C is not None):
                self.player_C.quit()
            if (self.player_D is not None):
                self.player_D.quit()
            # Since OmxPlayer sucks ass and cannot be started while on mute, we have to set the volume
            # to a stupidly high value (10000) so that it will overflow and start the player in a muted state.
            # Thus, passing --vol 100000 argument.
            self.player_C = OMXPlayer(previous_video,
                args=['--layer', 0, '--vol', 100000],
                dbus_name='org.mpris.MediaPlayer2.omxplayerC')
            self.player_C.dbus_name = "org.mpris.MediaPlayer2.omxplayerC"
            self.player_C.playerIdentifier = "Player A - " + previous_video
            self.previous_player = self.player_C

    def prepareVideos(self):

        # Establish next / previous indexes
        if (self.current_video_index + 1) >= len(self.video_files):
                self.next_video_index = 0
        else:
            self.next_video_index = self.current_video_index + 1

        if (self.current_video_index - 1) < 0:
            self.previous_video_index = len(self.video_files) - 1
        else:
            self.previous_video_index = self.current_video_index - 1

        self.defineNextPlayer()
        self.definePreviousPlayer()

        # Sleep required otherwise the player will NOT be ready when doing the play/pause
        # This is really ugly practice but it does not seem that a more robust way is possible
        sleep(2)

        # Ugly hack to have the player paused on the first frames, play and pause again
        self.previous_player.play()
        self.previous_player.pause()
        self.next_player.play()
        self.next_player.pause()

    def waitForCurrentPlayerEnd(self):
        previousStatus = None
        while(True):
            try:
                self.currentStatus = self.current_player.playback_status()
                if (previousStatus != self.currentStatus):
                    previousStatus = self.currentStatus
                    print("Current player status: ", self.current_player.dbus_name, " - ", self.current_player.playback_status())
                if (self.current_player.position() > self.current_player.duration()):
                    print("Player should have stopped but keeps playing ... force quit.")
                    self.current_player.quit()
                    break
            except:
                print("Dbus error, player may be dead")
                self.current_player.quit()
                break

            sleep(0.1) # To avoid hoarding the ressources, no need to check that quickly

    def togglePlayPause(self):
        print("togglePlayPause")
        self.current_player.play_pause()

    def next(self):
        print("next")
        self.current_player.stop() # Stopping the player is wanted here

    def previous(self):
        print("previous")
        self.previousPerformed = True
        self.current_player.stop() # Stopping the player is wanted here

    def stop(self):
        print("Stopping current player")
        self.current_player.stop()

    def toggleScreen(self):
        print("toggleScreen")
        backlight_file = '/sys/class/backlight/rpi_backlight/bl_power'

        # Read the current backlight state
        with open(backlight_file, 'r') as file:
            current_state = file.read().strip()

        # Toggle the backlight state
        new_state = '0' if current_state == '1' else '1'

        # Write the new backlight state
        with open(backlight_file, 'w') as file:
            file.write(new_state)

        print(f"Backlight state toggled. New state: {new_state}")

        if (new_state == '1'):
            self.screen_disabled = True
            self.current_player.pause()
        elif (new_state == '0'):
            self.screen_disabled = False
            self.current_player.play()

    def on_key_press(self, event):
        key = event.name
        if key == '0' and not self.screen_disabled:
            self.togglePlayPause()
        elif key == '1' and not self.screen_disabled:
            if self.ready_for_next_previous:
                self.ready_for_next_previous = False
                self.next()
        elif key == '2' and not self.screen_disabled:
            if self.ready_for_next_previous:
                self.ready_for_next_previous = False
                self.previous()
        elif key == '3':
            self.toggleScreen()
        else:
            print("Key not supported : ", key)

    def loopAllVideos(self):

        # Prepare the initial video
        self.first_video_file = self.video_files[self.load_video_index()]
        self.player_A = OMXPlayer(self.first_video_file,
                args=['--layer', 10],
                dbus_name='org.mpris.MediaPlayer2.omxplayerA')
        self.player_A.dbus_name = "org.mpris.MediaPlayer2.omxplayerA"
        # Set current player
        self.current_player = self.player_A
        self.current_video_index = self.load_video_index()
        self.player_A.playerIdentifier = "Player A - " + self.first_video_file

        # Ugly but required for player to init ...
        sleep(3)

        # Infinite loop to play episodes endlessly.
        while(True):
            print("Current Index : " + str(self.current_video_index))
            # Start playback of current player
            print("Starting play of current player : ", self.current_player.playerIdentifier)
            self.save_video_index(self.current_video_index)

            # Set the volume to the default value (1) in order to restore audio that was muted when preparing the player.
            self.current_player.set_volume(1)
            self.current_player.play()
            self.current_player.set_layer(10)
            self.ready_for_next_previous = True

            # At each loop, prepare the other video to be played after the current one has stopped
            self.prepareVideos()

            # Wait for current player to end
            self.waitForCurrentPlayerEnd()

            if (self.previousPerformed):
                print("Previous requested, switching to player P")
                self.current_player = self.previous_player
                self.current_video_index = self.previous_video_index
                self.previousPerformed = False
            else:
                print("Play ended, switching to next player")
                self.current_player = self.next_player
                self.current_video_index = self.next_video_index

if __name__ == '__main__':

    # Instanciate GaplessPlayer
    gapless_player = GaplessPlayer("/home/azsde/SimpsonTv")

    # Hook keyboard key pressed
    keyboard.on_press(gapless_player.on_key_press)

    gapless_player.loopAllVideos()
