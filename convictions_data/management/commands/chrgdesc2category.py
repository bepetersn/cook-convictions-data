import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from convictions_data.models import Conviction
from convictions_data.statute import (get_iucr, IUCRLookupError,
    ILCSLookupError, StatuteFormatError)

from itertools import chain
import json


def update_or_create(dict, chrgdesc, category):
    if category:
        try:
            categories = dict[chrgdesc]
            if category not in categories:
                # uncomment next line to see multiple IUCR categories acrue
                #import pdb; pdb.set_trace()
                dict[chrgdesc].append(category)
        except KeyError:
            dict[chrgdesc] = [category]
    else:
        # warn if there's no IUCR category for this conviction
        assert False

FIRST_TIME = True

def true_once():
    global FIRST_TIME
    if FIRST_TIME:
        FIRST_TIME = not FIRST_TIME
        return True
    else:
        return False


class Command(BaseCommand):
    help = "Map charge descriptions to iucr categories."

    def handle(self, *args, **options):

        print('inside the command')

        chrgdesc_to_category = {}

        for conviction in Conviction.objects.all():

            if true_once():
                print('inside the iteration')

            chrgdesc = conviction.final_chrgdesc
            category = conviction.iucr_category

            case_number = conviction.case_number
            statute = conviction.final_statute
            chrgdispdate = conviction.chrgdispdate

            try:
                update_or_create(chrgdesc_to_category, chrgdesc, category)
            except AssertionError:
                
                #print ('NO IUCR found for conviction: {}').format(conviction)
                offense_tuples = set()
                for conviction in Conviction.objects.filter(final_chrgdesc=chrgdesc):
                    try:
                        offense_tuples.add(tuple(get_iucr(conviction.final_statute)))
                    except IUCRLookupError:
                        #print ("UNKNOWN CODE associated /w chrgdesc: {}").format(chrgdesc)
                        pass
                    except ILCSLookupError:
                        #print ("UNKNOWN STATUTE associated /w chrgdesc: {}").format(chrgdesc)
                        pass
                    except StatuteFormatError:
                        #print ("UNKNOWN FORAMT associated /w chrgdesc: {}").format(chrgdesc)
                        pass

                if len(offense_tuples) == 1:
                    #print 'SAME IUCRs from every conviction' 
                    offenses = list(offense_tuples)[0]
                    if len(set(o.offense_category for o in offenses)) == 1:
                        #print 'SAME CATEGORY for all the IUCRs'
                        category = offenses[0].offense_category
                        if category:
                            #print('SUCCESS: All convictions /w this chrgdesc ({}) have the '
                                #'same iucr category ({})').format(chrgdesc, category)
                            update_or_create(chrgdesc_to_category, chrgdesc, category)
                        else:
                            #print 'something weird is going on'
                            pass
                    else:
                        #print "Couldn't get an IUCR category for this"
                        pass

        print('num total: ', len(chrgdesc_to_category))
        print 'writing file with all'
        with open('chrgdesc_to_category__all.json', 'w') as f:
            json.dump(chrgdesc_to_category, f)

        print 'sorting'
        chrgdesc_to_category = {x: chrgdesc_to_category[x] for x in chrgdesc_to_category.keys() if len(chrgdesc_to_category[x]) > 1}
        
        print('num with multiple: ', len(chrgdesc_to_category))
        print 'writing mutliples file'
        with open('chrgdesc_to_category__multiples.json', 'w') as f:
            json.dump(chrgdesc_to_category, f)

        print 'done'




