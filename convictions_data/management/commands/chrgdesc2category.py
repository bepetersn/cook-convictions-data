from __future__ import division

from django.core.management.base import BaseCommand

from convictions_data.models import Conviction
from convictions_data.statute import (get_iucr, IUCRLookupError,
    ILCSLookupError, StatuteFormatError)

import json


FIRST_TIME = True

def true_once():
    global FIRST_TIME
    if FIRST_TIME:
        FIRST_TIME = not FIRST_TIME
        return True
    else:
        return False


def div(x, y):
    try:
        return round((x / y), 4) * 100
    except ZeroDivisionError:
        return 0


def update_or_create(dict, chrgdesc, new_categories):
    try:
        present_categories = dict[chrgdesc]
        for c in new_categories:
            if c not in present_categories:
                dict[chrgdesc].append(c)
    except KeyError:
        dict[chrgdesc] = new_categories


class Command(BaseCommand):
    help = \
        """  
        Try to generate, as close as possible, 
        a one-to-one mapping between charge 
        descriptions and iucr categories.
        """

    def handle(self, *args, **options):

        print('inside the command')

        chrgdesc_to_category = {}
        hit = 0

        convictions = Conviction.objects.all()
        total = convictions.count()

        for i, conviction in enumerate(convictions):

            if true_once():
                print('inside the iteration')

            chrgdesc = conviction.final_chrgdesc
            category = conviction.iucr_category
            statute = conviction.final_statute

            # if exactly one IUCR code / category is associated
            # with this conviction, map it to the conviction's
            # charge description;

            # also make sure that the category can be found in the crosswalk's 
            # list of possible categories and is not just somehow in the database
            if category and category not in [o.offense_category for o in get_iucr(statute)]:
                category = ''

            if category:
                update_or_create(chrgdesc_to_category, chrgdesc, [category])
                hit += 1

            # otherwise, check if the conviction doesn't have an IUCR
            # because multiple possible IUCRs matched the conviction's statute   
            else:                
                try:
                    offenses = get_iucr(statute)
                except IUCRLookupError:
                    continue
                except ILCSLookupError:
                    continue
                except StatuteFormatError:
                    continue

                if len(offenses) >= 1:
                    # if so, check if all possible IUCRs associated with
                    # that statute map to a single charge description;
                    if len(set([o.offense_category for o in offenses])) == 1:
                        category = offenses[0].offense_category

                        update_or_create(chrgdesc_to_category, chrgdesc, [category])
                        hit += 1
                    else:
                        categories = list(set([o.offense_category for o in offenses]))
                        update_or_create(chrgdesc_to_category, chrgdesc, categories)

            print "{}% one-to-one mapping".format(div(hit, i))

        print 'num total: ', len(chrgdesc_to_category)
        print 'writing file with all'
        with open('chrgdesc_to_category__all.json', 'w') as f:
            json.dump(chrgdesc_to_category, f)

        chrgdesc_to_category_multiples = {x: chrgdesc_to_category[x] for x in chrgdesc_to_category.keys() if len(chrgdesc_to_category[x]) > 1}
        
        print 'num chrgdesc that map to multiple possible IUCR categories: ', len(chrgdesc_to_category_multiples)
        print 'writing multiples file'
        with open('chrgdesc_to_category__multiples.json', 'w') as f:
            json.dump(chrgdesc_to_category_multiples, f)

        print ('num convictions whose chrgdesc maps to multiple possible '
              'IUCR categories: {}').format(total - hit)

        print 'done'




