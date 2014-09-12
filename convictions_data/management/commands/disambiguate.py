from __future__ import division

from django.core.management.base import BaseCommand
from django.db.models import Count

from convictions_data.models import Conviction
from convictions_data.statute import get_iucr, IUCRLookupError, \
    ILCSLookupError, StatuteFormatError

import json, sys


def prefix_fmt(num_break):
    return '    ' * num_break

def suffix_fmt(num_break):
    return '\n' * num_break

def fmt(msg, prefix, suffix):
    prefix = prefix_fmt(prefix)
    suffix = suffix_fmt(suffix)
    print "{0}{1} ...{2}".format(prefix, msg, suffix)

def fmt_item(name, item, prefix, suffix):
    if not item:
        item = 'This value is empty.'
        
    msg='{}: {}'.format(name, item)
    fmt(msg, prefix, suffix)

def set_formatting(loop_level):
    # no indent, two newlines
    # at first loop level
    if loop_level == 0:
        return 0, 2

    # one indent, two new lines
    # at second loop level
    if loop_level == 1:
        return 1, 2

    # two indents, one new line
    # at third loop level
    if loop_level == 2:
        return 2, 1


class Command(BaseCommand):
    help = \
        """  
        Do some work...
        """

    def handle(self, *args, **options):

        with open('chrgdesc_to_category__multiples.json') as f:

            START_LOOP = 0
            prefix = None
            suffix = None

            multiples = json.load(f)

            print '\n'
            print 'Total num of multiples: {}'.format(len(multiples))
            print '\n\n'

            for chrgdesc in multiples:

                loop_level = START_LOOP
                prefix, suffix = set_formatting(loop_level)

                fmt_item('chrgdesc', chrgdesc, prefix, 0)

                convictions = Conviction.objects.filter(final_chrgdesc=chrgdesc).values('final_statute').annotate(Count('id')).order_by()
                num_convictons = convictions.count()
                fmt('Num of statutes: {}'.format(num_convictons), prefix, suffix)

                for i, c in enumerate(convictions):

                    statute = c['final_statute']

                    loop_level = 1
                    prefix, suffix = set_formatting(loop_level)    

                    fmt_item('statute', statute, prefix, 0)
                    fmt('Num statutes left: {}'.format(num_convictons - (i+1)), prefix, suffix)                    
                    try:

                        loop_level = 2
                        prefix, suffix = set_formatting(loop_level)

                        o_tuples = [(o.code, o.offense_category) for o in get_iucr(statute)]
                        fmt_item('codes', [o[0] for o in o_tuples], prefix, suffix)
                        fmt_item('categories', [o[1] for o in o_tuples], prefix, suffix)
                        
                    except IUCRLookupError:
                        fmt('IUCRLookupError occurred', prefix, suffix)
                    except ILCSLookupError:
                        fmt('ILCSLookupError occurred', prefix, suffix)
                    except StatuteFormatError:
                        fmt('StatuteFormatError occurred', prefix, suffix)

                    finally:

                        try:
                            cmd = raw_input('>> ')
                        except KeyboardInterrupt:
                            print '\ndone!'
                            sys.exit(0)

                        if cmd == 'n':
                            break
                        print '\n'

        print 'done!'




