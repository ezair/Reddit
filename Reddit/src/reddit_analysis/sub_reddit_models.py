"""
LATER
"""
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import RegexpTokenizer
from nltk.stem import PorterStemmer
from nltk.classify import NaiveBayesClassifier


class SubRedditAnalyzer():
    """
    More on this later.
    """

    def __init__(self, mongo_reddit_collection):
        # This needs to be done, so that we can actually grab data from nltk.

        """ The MongDB collection that we will be pulling our reddit data from."""
        self.__reddit_collection = mongo_reddit_collection

        """
        Since we are analyzing english, we will use a already created (and tested)
        set of stopwords that.
        Every word in here is a word that is not worth analyzing in a given comment.
        These are the kind of words that can make or break your analysis results.
        """
        self.__stop_words = stopwords.words('english')

    def __preprocess_comment_for_analysis(self, comment):
        filtered_tokens_in_comment = []
        for sentence in comment:
            # We don't wanna have any punctuation in our comment.
            tokenizer = RegexpTokenizer(r'\w+')
            tokenized_sentence = tokenizer.tokenize(sentence)

            # We do not care about words in our stop list, they just cause issues.

            for token in tokenized_sentence:
                if token.to_lower() not in self.__stop_words:
                    filtered_tokens_in_comment.append(token)

        # Now we stem each token in the commen that we have.
        # E.g. Words like 'run' or 'running' just become their base form word 'run'
        stemmer = PorterStemmer()
        stemed_tokens = [stemmer.stem(token) for token in filtered_tokens_in_comment]

        # Finally, we want to look at each token and get its tagging.
        # E.g. is it a noun, a verb, what is it?
        preprocessed_tokens = nltk.pos_tag(stemed_tokens)
        print(preprocessed_tokens)
        print(type(preprocessed_tokens))
        return preprocessed_tokens

    def analyze_submission(self, submission_id_as_string, show_statistics=False,
                           show_most_frequent_words=False):
        all_submission_comment_objects = \
            self.__reddit_collection.find({'submission': submission_id_as_string})

        # We need to get the actual text from our commend objects, since that is
        # what is going to be analyzed.
        all_comments_on_submission_as_strings = \
            [comment['body'] for comment in all_submission_comment_objects]

        # Okay, we have now cleaned up each individual comment in the given list,
        # so they are ready to be analysed.
        all_processed_comments = []

        self. __preprocess_comment_for_analysis(all_comments_on_submission_as_strings)

        # Now, let's find out what is "positive" and what is "negative".
        # We can get an overall rating of "goodness" and "badness" based off of this.
        pos_freq = nltk.FreqDist(all_processed_comments)
        print(pos_freq.most_common(30))

        if show_statistics:
            pass

    def analyze_whole_subreddit(self, subreddit_name):
        pass