#!/usr/bin/env python

from getpass import getpass
import sys
from google import Mobileclient
from collections import defaultdict
from time import sleep
import urllib
import urllib2
import json
import os
import argparse
import platform


if ".exe" in sys.argv[0]:
        os.environ['REQUESTS_CA_BUNDLE'] = os.path.join(os.getcwd(), 'cacert.pem') ## This is needed to make the .exe version work

try:
        import certifi
except:
        print "You need to easy_install certifi"
        input("Press enter to exit")
        sys.exit()
try:
        import gpsoauth
except:
        print "You need to easy_install gpsoauth"
        input("Press enter to exit")
        sys.exit()

try:
        input = raw_input
except NameError:
        pass

spotifyDumpFile='ezportify-tracks.txt'

def win_getpass(prompt='Password: ', stream=None):
        """Prompt for password with echo off, using Windows getch()."""
        if sys.stdin is not sys.__stdin__:
                return fallback_getpass(prompt, stream)
        import msvcrt
        for c in prompt:
                msvcrt.putch(c)
        pw = ""
        while 1:
                c = msvcrt.getwch()
                if c == '\r' or c == '\n':
                        break
                if c == '\003':
                        raise KeyboardInterrupt
                if c == '\b':
                        if pw == '':
                                pass
                        else:
                                pw = pw[:-1]
                                msvcrt.putch('\b')
                                msvcrt.putch(" ")
                                msvcrt.putch('\b')
                else:
                        pw = pw + c
                        msvcrt.putch("*")
        msvcrt.putch('\r')
        msvcrt.putch('\n')
        return pw

def hitapi(oauth, url):
        headers = { 'Authorization' : 'Bearer ' +  oauth}
        req = urllib2.Request(url, headers=headers)
        try:
                response = urllib2.urlopen(req)
        except urllib2.HTTPError, e:
                response = e.fp
        the_page = response.read()
        return json.loads(the_page)

def googlelogin():
        google_email = input("Enter Google email address: ")
        if platform.system() == "Windows":
                google_pass = win_getpass("Enter Google password: ")
        else:
                google_pass = getpass("Enter Google password: ")

        googleapi = Mobileclient()
        google_loggedin = googleapi.login(google_email, google_pass)
        if not google_loggedin:
                print "Invalid Google username/password"
                input("Press enter to exit")
                sys.exit()
        return googleapi

def dumpSpotify():
        print "Enter Spotify OAUTH Token from https://developer.spotify.com/web-api/console/get-current-user-playlists/ "
        oauth = input("Be sure to check the Relevant scopes checkbox: ")
        playlists = hitapi(oauth, 'https://api.spotify.com/v1/me/playlists')
        if 'error' in playlists.keys():
                print "The oauth token is invalid"
                print "Make sure you check the checkbox or checkboxes under 'Relevant scopes'. Clear your token and try again if needed"
                input("Press enter to exit")
                sys.exit()
        items = playlists['items']
        while playlists['next']:
                playlists = hitapi(oauth, playlists['next'])
                items += playlists['items']
        print len(items)

        f = open(spotifyDumpFile, 'w')

        for playlist in items:
                try:
                        print playlist
                        print playlist['name']
                        f.write('\n:::' + playlist['name'] + ":::\n")
                        queries = []
                        trackresp = hitapi(oauth, playlist['href'])['tracks']
                        tracks = trackresp['items']
                        while trackresp['next']:
                                sys.stdout.write(".",0)
                                trackresp = hitapi(oauth, trackresp['next'])
                                tracks += trackresp['items']
                        print ""
                        ot = 1
                        for track in tracks:
                                try:
                                        searchstr = ''
                                        if 'artists' in track['track'].keys() and track['track']['artists']:
                                                searchstr += track['track']['artists'][0]['name'] + ' - '
                                        searchstr += track['track']['name']
                                        searchstr_ascii = searchstr.encode("utf-8", "replace")
                                        f.write(searchstr_ascii + "\n")
                                except Exception as e:
                                        print "----"
                                        print e
                                        print "----"
                                        #print 'Track', ot, 'Failed'
                                ot += 1
                except:
                        print playlist['name'], 'Failed to copy. Skipping'

        f.close()

def main(args):
    if not args.dump:
        googleapi = googlelogin()

    if args.import_file is None:
        dumpSpotify()
        importFile = open(spotifyDumpFile,'r')
    else:
        importFile = args.import_file


    playlistName='INITIAL_USELESS_PLAYLIST_NAME'
    gInfo = defaultdict(list)
    with importFile as playlist_and_songs:
        for item in playlist_and_songs:
            '''
            - Playlists start with :::
            - Songs are formatter as 'Artist - title'
            - emptyline as delimiter
            '''
            if item[0:3] == ':::':
                playlistName = item[3:-4]
                print "PLAYLIST: %s " % ( playlistName )
            elif item != '\n':
                #print "SONG : ", item

                sleep(0.3)

                gtrack = None
                if not args.dump:
                    gtrack = googleapi.find_best_track(item)
                    if gtrack:
                            gInfo[playlistName].append(gtrack['nid'])
                            print 'found', item
                    else:
                        print 'Not found: Playlist "%s" , song "%s" ' %( playlistName, item[:-1])

    # create objects for play list, tracks in googleapi...
    for playlist in gInfo:
        gtracks= []
        for song in gInfo[playlist]:
            gtracks.append(song)

        print "Creating in Google Music playlist %s with songs : %s" % ( playlist, gtracks)

        playlist_id = googleapi.create_playlist(playlist)
        googleapi.add_songs_to_playlist(playlist_id, gtracks)
        print "Done playlist %s" % ( playlist )
        sleep(2)


    input("Press enter to exit")

if __name__ == '__main__':
        parser = argparse.ArgumentParser(description='Spotify To Google Playlist Transcription')
        parser.add_argument("-d", "--dump", help="Only Dump Playlists To File",
                                        action="store_true")

        parser.add_argument("-i","--import_file", help="Skip spotify, load playlists and tracks from file passed here",
                            type=argparse.FileType('r'), default=None)

        parser.add_argument('--version', action='version', version='%(prog)s 0.4')
        args = parser.parse_args()
        main(args)
