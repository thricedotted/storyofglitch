#!/usr/bin/env python2
# -*- coding: utf-8 -*- #

from twitterbot import TwitterBot

#from anthrobot import config, actions, characteristics

import arrow

import random
import os
import logging
import re
import numpy as np

from blacklist import BLACKLIST
from credentials import *

"""
class Kitty(config.Config):
    nouns = ["cat", "kitty"]
    action_articles = ['', "sometimes my"]
    action_verbs = ['', "is", "just"]

    def reject_tweet(self, tweet):
        return any(w in tweet.lower() for w in BLACKLIST)
"""


class StoryOfGlitch(TwitterBot):
    def bot_init(self):
        self.config['api_key'] = CONSUMER_KEY
        self.config['api_secret'] = CONSUMER_SECRET
        self.config['access_key'] = ACCESS_TOKEN
        self.config['access_secret'] = ACCESS_TOKEN_SECRET

        # use this to define a (min, max) random range of how often to tweet
        self.config['tweet_interval_range'] = (10*60, 40*60)

        # only reply to tweets that specifically mention the bot
        self.config['reply_direct_mention_only'] = False

        # only include bot followers (and original tweeter) in @-replies
        self.config['reply_followers_only'] = True

        # fav any tweets that mention this bot?
        self.config['autofav_mentions'] = False

        # fav any tweets containing these keywords?
        self.config['autofav_keywords'] = ["glitch"]

        # follow back all followers?
        self.config['autofollow'] = True

        # ignore home timeline tweets which mention other accounts?
        self.config['ignore_timeline_mentions'] = False

        # max number of times to reply to someone within the moving window
        self.config['reply_threshold'] = 3

        # length of the moving window, in seconds
        self.config['recent_replies_window'] = 20*60

        # probability of replying to a matching timeline tweet
        self.config['timeline_reply_probability'] = 0.001

        # probability of tweeting an action, rather than a characteristic
        self.config['action_probability'] = 0.8

        #self.config['silent_mode'] = (int(os.environ.get('SILENT_MODE', '1')) != 0)
        self.config['silent_mode'] = 0

    def on_scheduled_tweet(self):
        text = self.generate_tweet(max_len=140)

        if self._is_silent():
            self.log("Silent mode is on. Would've tweeted: {}".format(text))
            return

        self.post_tweet(text)

    def on_mention(self, tweet, prefix):
        if not self.check_reply_threshold(tweet, prefix):
            return

        self.reply_to_tweet(tweet, prefix)

    def on_timeline(self, tweet, prefix):
        if not self.check_reply_threshold(tweet, prefix):
            return

        if random.random() > self.config['timeline_reply_probability']:
            self.log("Failed dice roll. Not responding to {}".format(self._tweet_url(tweet)))
            return

        self.reply_to_tweet(tweet, prefix)

    def reply_to_tweet(self, tweet, prefix):
        prefix = prefix + ' '
        text = prefix + self.generate_tweet(max_len=140-len(prefix), reply=True)

        if self._is_silent():
            self.log("Silent mode is on. Would've responded to {} with: {}".format(self._tweet_url(tweet), text))
        else:
            self.post_tweet(text, reply_to=tweet)

        self.update_reply_threshold(tweet, prefix)

    def _is_silent(self):
        return self.config['silent_mode']

    def check_reply_threshold(self, tweet, prefix):
        self.trim_recent_replies()
        screen_names = self.get_screen_names(prefix)
        over_threshold = [sn for sn in screen_names if self.over_reply_threshold(sn)]

        if len(over_threshold) > 0:
            self.log("Over reply threshold for {}. Not responding to {}".format(", ".join(over_threshold), self._tweet_url(tweet)))
            return False

        return True

    def over_reply_threshold(self, screen_name):
        replies = [r for r in self.recent_replies() if screen_name in r['screen_names']]
        return len(replies) >= self.config['reply_threshold']

    def update_reply_threshold(self, tweet, prefix):
        screen_names = self.get_screen_names(prefix)

        self.recent_replies().append({
            'created_at': arrow.utcnow(),
            'screen_names': screen_names,
        })

        self.log("Updated recent_replies: len = {}".format(len(self.recent_replies())))

    def get_screen_names(self, prefix):
        return [sn.replace('@', '') for sn in prefix.split()]

    def trim_recent_replies(self):
        len_before = len(self.recent_replies())
        now = arrow.utcnow()
        self.state['recent_replies'] = [
            r for r in self.recent_replies()
            if (now - r['created_at']).seconds < self.config['recent_replies_window']
        ]
        self.log("Trimmed recent_replies: {} -> {}".format(len_before, len(self.recent_replies())))

    def recent_replies(self):
        if 'recent_replies' not in self.state:
            self.state['recent_replies'] = []
        return self.state['recent_replies']

    def generate_tweet(self, max_len, reply=False):
        emote = ''
        if random.random() > 0.7:
            emote = ' ' + random.choice([':3', '=^.^=', '^3^', 'o3o'])

        second_person = ['u', 'ur', 'urs', 'u\'ve']

        #cfg = Kitty()
        candidates = self.generate_candidates(cfg)
        candidates = [c for c in candidates if len(c) + len(emote) <= max_len]

        if reply and len(candidates) > 1:
            candidates = [c for c in candidates if any(w in c.split() for w in second_person)]

        if len(candidates) == 0:
            raise Exception("No suitable candidates were found")

        return random.choice(candidates) + emote

    def generate_candidates(self, cfg):
        #TODO: continually mine tweets for actions, etc

        die = random.random()

        if die < 0.7:
            with open('unique_actions') as f:
                tweets = random.sample(f.readlines(), 100)
            return ['*%s*' % a.strip() for a in tweets]
        elif die < 0.85:
            with open('unique_characteristics') as f:
                tweets = random.sample(f.readlines(), 100)
            return ['(im %s)' % a.strip() for a in tweets]
        elif die < 0.95:
            return [self.cat_talk('meow')]
        else:
            return [self.cat_talk('purr')]


    def cat_talk(self, mode=None):
        weights = np.array([1/(1+n) for n in xrange(5)])
        
        say = ''

        if mode == 'meow' or mode is None:
            for _ in xrange(np.random.choice(range(1,5), p=(weights[:-1] / weights[:-1].sum()))):
                say += 'm'
                
                say += np.random.choice(range(1,5), p=(weights[:-1] / weights[:-1].sum())) * 'e'
                if np.random.random() > 0.1:
                    say += np.random.choice(range(1,5), p=(weights[:-1] / weights[:-1].sum())) * 'o'
                say += np.random.choice(range(1,5), p=(weights[:-1] / weights[:-1].sum())) * 'w'

                say += ' '

            say = say.strip()

            if np.random.random() > 0.3:
                say += np.random.choice(['.', '!', '...', '~', '?']) * np.random.choice(range(1,4), p=(weights[:-2] / weights[:-2].sum()))

        else:
            for _ in xrange(np.random.choice(range(1,5), p=(weights[:-1] / weights[:-1].sum()))):
                say += 'pu'
                
                say += np.random.choice(range(1,5), p=(weights[:-1] / weights[:-1].sum())) * 'r'
                say += np.random.choice(range(1,5), p=(weights[:-1] / weights[:-1].sum())) * 'r'

                say += ' '

        return say.strip()

if __name__ == '__main__':
    stderr = logging.StreamHandler()
    stderr.setLevel(logging.DEBUG)
    stderr.setFormatter(logging.Formatter(fmt='%(levelname)8s: %(message)s'))

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(stderr)

    bot = StoryOfGlitch()
    bot.run()
