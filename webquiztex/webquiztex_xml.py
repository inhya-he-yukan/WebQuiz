r'''
-----------------------------------------------------------------------------
    webquiztex_xml | xml reader for reading the xml file generated by tex4ht
-----------------------------------------------------------------------------

    Copyright (C) Andrew Mathas and Donald Taylor, University of Sydney

    Distributed under the terms of the GNU General Public License (GPL)
                  http://www.gnu.org/licenses/

    This file is part of the Math_quiz system.

    <Andrew.Mathas@sydney.edu.au>
    <Donald.Taylor@sydney.edu.au>
-----------------------------------------------------------------------------
'''

# -*- encoding: utf-8 -*-

import xml.sax

# imports of webquiz code
from webquiztex_util import debugging, webquiztex_error

# ---------------------------------------------------------------------------------------
def ReadWebQuizXmlFile(quizfile, defaults):
    r'''
    Set up, call and then return the xml parser
    for the quiz web page
    '''
    parser = xml.sax.make_parser()
    quiz = QuizHandler(defaults)
    parser.setContentHandler(quiz)
    parser.setErrorHandler(quiz)
    parser.setDTDHandler(quiz) # as far as I can see this does nothing...
    parser.parse(quizfile)
    parser.close()
    return quiz


# ---------------------------------------------------------------------------------------
class Data(object):
    r'''
    A wrapper object class that holds the data for the different
    components of the quiz.
    '''
    def __init__(self, **args):
        '''
        Accepts key-value pairs, each of which is stored as an attribute
        '''
        self._items = args.items()
        for key, val in args.items():
            setattr(self, key, val)

    def __str__(self):
        r'''
        A string method, purely for debugging purposes...
        '''
        return '\n - '.join('{} = {}'.format(k, getattr(self, k)) for k in self._items)


class QuizHandler(xml.sax.ContentHandler):
    """
        The content handler gives the xml tags to `startElement`, which
        initialises the webquiztex tags, and then `endElement` attaches the
        content of each webquiztex tag tothe appropriate part of `self`. Any end
        tag that is ot special to webquiztex has its contents appended to
        `self.text`. Any tag that contains `DeFaUlT` is set to the system
        default using the `defaults` dictionary.
    """

    def __init__(self, defaults):
        self.defaults = defaults

        # arrays for the different quiz components
        self.discussion_list = []
        self.question_list = []
        self.quiz_index = []

        # these will contain the link and meta elements from the xml file but they
        # are ignored by webquiztex.py
        self.link_list = []
        self.meta_list = []

        # to add mathjs when an eval comparison is used
        self.mathjs = False

        # the following tags have defaults set by `defaults`
        self.setting_tags = [
               'department',
               'department_url',
               'institution',
               'institution_url',
               'language',
               'theme',
        ]
        # quiz data
        for tag in self.setting_tags:
            setattr(self, tag, defaults[tag])
        self.breadcrumb = ''
        self.text = ''
        self.after_text = ''
        self.title = ''
        self.unit_code = ''
        self.unit_name = ''

        # keep track of current tags for debugging...
        self.current_tags=[]


    def Debugging(self, msg):
        r'''
            Customised debugging message for the xml module
        '''
        debugging(self.defaults.debugging, 'xml: ',msg)

    def set_default_attribute(self, key, value):
        ''' Set the attribute `key` of self, using the default value if
        `value=='DeFaUlT'`.
        '''
        if value.strip() == 'DeFaUlT':
            setattr(self, key, self.defaults[key])
        else:
            setattr(self, key, value)
        self.Debugging('Just set "{}" equal to "{}" from "{}"'.format(key, getattr(self, key), value))

    #---- start of start elements --------------------------------------------
    def startElement(self, tag, attributes):
        '''
            At the start of each webquiztex xml tag we need to pull out the
            attributes and place
        '''
        self.Debugging('Starting tag for '+tag)
        self.current_tags.append(tag)

        if hasattr(self, 'start_'+tag):
            getattr(self, 'start_'+tag)(attributes)

        elif tag in ['department', 'institution', 'uni']:
            for key in attributes.keys():
                self.set_default_attribute(tag, attributes.get(key))

    def start_webquiztex(self, attributes):
        r'''
        Start element for tag="webquiztex". Initialise the quix and extract
        and process the list of attributes.
        '''
        for key in attributes.keys():
            self.set_default_attribute(key, attributes.get(key))

        # convert the following attibutes to booleans
        for key in ['debugging', 'hide_side_menu', 'one_page', 'pst2pdf', 'random_order', 'save_state']:
            setattr(self, key, getattr(self, key)=='true')

        setattr(self, 'language', self.language.lower())
        setattr(self, 'theme', self.theme.lower())

        # set debugging mode from the latex file...from this point on
        self.defaults.debugging = self.defaults.debugging or self.Debugging


    def start_link(self, attributes):
        r'''
        Start element for tag="link"
        '''
        self.link_list.append({key: attributes.get(key) for key in attributes.keys()})

    def start_meta(self, attributes):
        r'''
        Start element for tag="meta"
        '''
        self.meta_list.append({key: attributes.get(key) for key in attributes.keys()})

    def start_breadcrumb(self, attributes):
        r'''
        Start element for tag="breadcrumb"
        '''
        self.set_default_attribute('breadcrumbs', attributes.get('breadcrumbs'))

    def start_unit_name(self, attributes):
        r'''
        Start element for tag="unit_name"
        '''
        self.set_default_attribute('unit_url', attributes.get('url'))
        self.quizzes_url = attributes.get('quizzes_url')
        if self.quizzes_url == 'DeFaUlT':
            self.quizzes_url = self.unit_url + '/Quizzes'

    def start_discussion(self, attributes):
        r'''
        Start element for tag="discussion"
        '''
        discussion = Data(heading = '',
                          short_heading = '',
                          text = ''  # The text of the discussion
        )
        self.discussion_list.append(discussion)

    def start_question(self, attributes):
        r'''
        Start element for tag="question"
        '''
        self.question_list.append(
            Data(text = '',      # The text of the question
                type = None,    # input, or single or multiple choice
                after_text = '' # text at end of question
            )
        )

    def start_answer(self, attributes):
        r'''
        Process the different question types, items choice and feedback
        '''
        if self.question_list[-1].type != None:
            webquiztex_error('question {} has too many question types: {} and input'.format(
                    len(self.question_list)+1, self.question_list[-1].type)
            )
        self.question_list[-1].type = 'input'
        self.question_list[-1].answer = ''
        self.question_list[-1].feedback_right = ''
        self.question_list[-1].feedback_wrong = ''
        self.question_list[-1].text += self.text
        self.text = ''

        self.question_list[-1].comparison = attributes.get('comparison')
        self.question_list[-1].prompt = attributes.get('prompt')=='true'
        if self.question_list[-1].comparison in ['complex', 'number']:
            self.mathjs = True

    def start_choice(self, attributes):
        r'''
        Start element for tag="choice"
        '''
        if self.question_list[-1].type != None:
            webquiztex_error('question {} has too many question types: {} and choice'.format(
                    len(self.question_list)+1, self.question_list[-1].type)
            )
        self.question_list[-1].type = attributes.get('type')
        self.question_list[-1].columns = int(attributes.get('columns'))
        self.question_list[-1].items = []
        self.question_list[-1].correct = 0
        self.question_list[-1].text += self.text
        self.text = ''

    def start_item(self, attributes):
        r'''
        Start element for tag="item"
        '''
        self.question_list[-1].items.append(
                Data(correct= attributes.get('correct'),
                     symbol=attributes.get('symbol'),
                     feedback='',
                     text=''
                    )
        )
        if attributes.get('correct')=='true':
            self.question_list[-1].correct += 1

    def start_index_item(self, attributes):
        r'''
        Finally look after the index file
        '''
        self.quiz_index.append(Data(
                prompt=attributes.get('prompt')=='true',
                url=attributes.get('url'),
                title=''
            )
        )

    def start_when(self, attributes):
        r'''
        start element for tag="when"
        '''
        if self.text.strip() != '':
            self.question_list[-1].after_text += ' '+self.text.strip()
            self.Debugging('After_text is now {}'.format(self.question_list[-1].after_text))
            self.text = ''
        self.current_tags[-1] = 'feedback_'+attributes.get('type')

    #---- end of start elements ---------------------------------------------

    def endElement(self, tag):
        self.Debugging('ending tag for {} (should be {})'.format(tag, self.current_tags[-1])) 

        reset_text = True
        if hasattr(self, 'end_'+tag):
            getattr(self, 'end_'+tag)()
            self.text = ''

        elif tag in self.setting_tags:
            self.set_default_attribute(tag, self.text)
            self.text = ''

        elif tag in ['heading', 'short_heading']:
            setattr(self.discussion_list[-1], tag, self.text.strip())

        elif tag in ['breadcrumb', 'title', 'unit_code', 'unit_name']:
            setattr(self, tag, self.text.strip())

        else:
            # self.text lives to be used another day
            reset_text = False

        if reset_text:
            self.text = ''

        # remove the last tag from the tag list
        self.current_tags.pop()

    #---- start of the end elements ------------------------------------------

    def end_answer(self):
        r'''
        Process end tag when tag="answer"
        '''
        self.question_list[-1].answer = self.text.strip()

    def end_discussion(self):
        r'''
        Process end tag when tag="discussion"
        '''
        self.discussion_list[-1].text = self.text.strip()

    def end_item(self):
        r'''
        Process end tag when tag="item"
        '''
        self.question_list[-1].items[-1].text = self.text.strip()

    def end_feedback(self):
        r'''
        Process end tag when tag="feedback"
        '''
        self.question_list[-1].items[-1].feedback = self.text.strip()

    def end_question(self):
        r'''
        Process end tag when tag="question"
        '''
        # first some error checking
        if self.question_list[-1].type == None:
                webquiztex_error('Question {} does not have an \\answer or choice environment'.format(
                              len(self.question_list)+1))

        elif hasattr(self.question_list[-1], 'items'):
            if len(self.question_list[-1].items)==0:
                webquiztex_error('question {} has no multiple choice items'.format(
                              len(self.question_list)+1))

            if self.question_list[-1].type=='single' and self.question_list[-1].correct!=1:
                webquiztex_error('question {} is single-choice but has {} correct answers'.format(
                                len(self.question_list)+1,
                                self.question_list[-1].correct
                             )
                )
        elif not hasattr(self.question_list[-1], 'answer') or self.question_list[-1].answer=='':
            webquiztex_error('question {} does have not an \answer or multiple choice'.format(
                          len(self.question_list)+1))

        if self.text.strip() != '':
            self.question_list[-1].after_text += ' '+self.text.strip()

    def end_index_item(self):
        r'''
        Process end tag when tag="index_item"
        '''
        self.quiz_index[-1].title = self.text.strip().replace('\n',' ').replace('\r',' ')

    def end_when(self):
        r'''
        Process end tag when tag="index_item"
        '''
        self.Debugging('WHEN: Adding text to '+self.current_tags[-1])
        setattr(self.question_list[-1], self.current_tags[-1], self.text.strip())

    #---- end of end elements -----------------------------------------------

    def characters(self, text):  #data,start,length):
        r'''
        Append everything to `self.text`
        '''
        self.text += text

    def error(self, e):
        raise e

    def fatalError(self, e):
        raise e
