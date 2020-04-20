"""
LATER
"""

# For data preprocessing and frequency analysis.
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import RegexpTokenizer
from nltk.stem import PorterStemmer

# Catching possible mongo errors.
from pymongo.errors import CursorNotFound

# For analysis/gathering sentiment analysis results.
# Documentation of this analyzer:
# https://www.kaggle.com/kamote/exploring-toxic-comments-by-sentiment-analysis
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer 


class SubRedditAnalyzer():
    """
    More on this later.
    """


    def __init__(self, mongo_reddit_collection):
        # This needs to be done, so that we can actually grab data from nltk.

        """ 
        The MongDB collection that we will be pulling our reddit data Inside of.
        
        The database must have the following fielding fields in it:
            body, created_at, distinguished, edited, id, is_submitter
            link_id, parent_id, replies, score, stickied, submission
            subreddit, sorting_type': sorting_type
        """
        self.__reddit_collection = mongo_reddit_collection

        """
        Since we are analyzing english, we will use a already created (and tested)
        set of stopwords that.
        Every word in here is a word that is not worth analyzing in a given comment.
        These are the kind of words that can make or break your analysis results.
        """
        self.__stop_words = stopwords.words('english')

        """
        This is an out of the box Sentiment Analyzer model that is exceptionally good
        at analyzing social media data. We will feed individual comments to it and it will
        give us a score of polarity (positivity, negativity, neutral, and Compound). 
        """
        self.__comment_sentiment_analyzer = SentimentIntensityAnalyzer()

        # Make sure that the passed in database has all of the following fields.
        # It NEEDS to fit the form of our comment model, or we cannot analyze it.
        # TODO

    def __preprocess_comment(self, comment):
        filtered_tokens_in_comment = []
        # We don't wanna have any punctuation in our comment.
        tokenizer = RegexpTokenizer(r'\w+')
        tokenized_comment = tokenizer.tokenize(comment)

        # We do not care about words in our stop list, they just cause issues.
        for token in tokenized_comment:
            if token.lower() not in self.__stop_words:
                filtered_tokens_in_comment.append(token)

        # Now we stem each token in the commen that we have.
        # E.g. Words like 'run' or 'running' just become their base form word 'run'
        stemmer = PorterStemmer()
        stemed_tokens = [stemmer.stem(token) for token in filtered_tokens_in_comment]

        # Now, we wanna put these tokens back into string form, so that we can easily
        # feed them into our sentiment analyzer later on.\
        stemed_tokens_to_string_form = ' '.join(stemed_tokens)
        return stemed_tokens_to_string_form


    def __get_all_comment_objects_for_submission_and_sorting_type(self, submission_id,
                                                                  sorting_type):
        if sorting_type:
            if sorting_type not in ['hot', 'new', 'top']:
                # The user might not have passed in a valid sorting type, so we must account for that.
                raise ValueError('Error calling analyze_submission:, "{}" is not a valid option.'
                                 'Valid Options: "hot", "new, and "top"'.format(sorting_type))
            else:
                print(submission_id)
                return self.__reddit_collection.find({'submission': submission_id,
                                                      'sorting_type': sorting_type})

        # No sorting type given, so we can just get the query.
        return self.__reddit_collection.find({'submission': submission_id})

    def analyze_submission(self, submission_id, sorting_type=None,
                           display_all_comment_results=False):

        # Varying on the sorting type that is passed in, we will query on it.
        # if no sorting type is given, then we just grab all posts for the submission.
        print("submission id", submission_id)
        all_submission_comment_objects = \
            self.__get_all_comment_objects_for_submission_and_sorting_type(submission_id,
                                                                           sorting_type)
            
        for x in all_submission_comment_objects:
            print(x)
            print("i am here.")

        # We need to get the actual text from our comment object's body,
        # since that is what is going to be analyzed.
        all_comments_on_submission_as_strings = \
            [comment['body'] for comment in all_submission_comment_objects]

        # We have now cleaned up each individual comment in the given list, ready to analyze them.
        list_of_preprocessed_comments_for_submission = \
            [self.__preprocess_comment(comment)
             for comment in all_comments_on_submission_as_strings]

        analysis_comment_results_of_all_comments = []
        for comment in list_of_preprocessed_comments_for_submission:
            analysis_results_of_comment = self.__comment_sentiment_analyzer.polarity_scores(comment)
            analysis_comment_results_of_all_comments.append(analysis_results_of_comment)

            # The user wants us to show the scoring for all comments that we are analyzing.
            if display_all_comment_results:
                sub_reddit_name = \
                    self.__reddit_collection.find_one({'submission': submission_id})['subreddit_name']
                print("\nSubreddit Name:", sub_reddit_name)
                print("Comment:", comment)
                print("Positivity Rating:", analysis_results_of_comment['pos'])
                print("Negativity Results:", analysis_results_of_comment['neg'])
                print("Neutral results:", analysis_results_of_comment['neu'])

        try:
            average_positivity = (sum([comment_results['pos']
                                    for comment_results in analysis_comment_results_of_all_comments])
                                / len(analysis_comment_results_of_all_comments))

            average_negativity = (sum([comment_results['neg']
                                    for comment_results in analysis_comment_results_of_all_comments])
                                / len(analysis_comment_results_of_all_comments))

            average_neutrality = (sum([comment_results['neu']
                                    for comment_results in analysis_comment_results_of_all_comments])
                                / len(analysis_comment_results_of_all_comments))
        except ZeroDivisionError:
            # No comments exist for this, so we return default value.
            return {'positive': 0, 'negative': 0, 'neutral': 0}

        # They also wanna see the final results of scoring (even tho they are returned).
        if display_all_comment_results:
            print('\nResults of all comments for submission: "{}"'.format(submission_id))
            print("Average positivity: {}".format(average_positivity))
            print("Average negativity: {}".format(average_negativity))
            print("Average neutrality: {}".format(average_neutrality))

        return {
            'positive': average_positivity,
            'negative': average_negativity,
            'neutral':  average_neutrality
        }

    def analyze_subreddit(self, subreddit_name, sorting_type=None,
                          display_all_comment_results=False,
                          display_all_submission_results=False):
        average_results_for_sub_reddit = {
            'positive': 0,
            'negative': 0,
            'neutral': 0
        }

        # Every single subreddit submission record (with given sorting type).
        all_sub_reddit_submissions = \
            self.__reddit_collection.find({'subreddit_name': subreddit_name})
        print(all_sub_reddit_submissions)
        for submission in all_sub_reddit_submissions:
            
            # Dict with all averages of a submission in given subreddit.
            analysis_results_of_submission = \
                self.analyze_submission(submission['_id'], sorting_type=sorting_type,
                                        display_all_comment_results=display_all_comment_results)
            
            print(submission)
            print(analysis_results_of_submission)
            average_results_for_sub_reddit['positive'] += analysis_results_of_submission['positive']
            average_results_for_sub_reddit['negative'] += analysis_results_of_submission['negative']
            average_results_for_sub_reddit['neutral'] += analysis_results_of_submission['neutral']

            # print("submission results", str(average_results_for_sub_reddit))

            # They want to see the rating for each submission post.
            if display_all_submission_results:
                print("{}: ".format(subreddit_name))
                print('Positivity Rating: {}'.format(average_results_for_sub_reddit['positive']))
                print('Negativity Rating: {}'.format(average_results_for_sub_reddit['negative']))
                print('Neutrality Rating: {}'.format(average_results_for_sub_reddit['neutral']))

        # There might be zero submissions; avoid dividing by zero :)
        try:
            average_results_for_sub_reddit['positive'] /= all_sub_reddit_submissions.retrieved
            average_results_for_sub_reddit['negative'] /= all_sub_reddit_submissions.retrieved
            average_results_for_sub_reddit['neutral'] /= all_sub_reddit_submissions.retrieved
        except ZeroDivisionError:
            # Nothing was retrieved, so we return default.
            return {'positive': 0, 'negative': 0, 'neutral': 0}

        # The wanna show the averages in the method.
        if display_all_submission_results:
            print('\nResults of all comments for submission: "{}"'.format(subreddit_name))
            print("Average positivity: {}".format(average_results_for_sub_reddit['positive']))
            print("Average negativity: {}".format(average_results_for_sub_reddit['negative']))
            print("Average neutrality: {}".format(average_results_for_sub_reddit['neutral']))

        return average_results_for_sub_reddit

    # Later, once I implement word bubble and freq analysis.
    def show_hotest_submission_topics(self, submission_id):
        pass

    # Later, once I implement word bubble and freq analysis.
    def show_hotest_sub_reddit_topics(self, subreddit_id):
        pass
