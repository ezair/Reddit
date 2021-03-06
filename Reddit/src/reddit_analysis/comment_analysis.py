"""
@Author Eric Zair
@File comment_analysis.py
@Description: Contains an object, SubredditAnalyzer, which is used for running sentiment analysis on
              the comments of a given subreddit or a given submission. The comments that we are
              analyzing are stored in a mongodb database.

@package docstring
"""
# We want to know how long the analysis of a subreddit takes, should the user want to see the results.
import datetime

# Catching possible mongo errors.
from pymongo.errors import CursorNotFound

# My comment preprocessor object, specifically used for reddit comments.
from .comment_preprocessing import RedditPreprocessor

# For analysis/gathering sentiment analysis results.
# https://www.kaggle.com/kamote/exploring-toxic-comments-by-sentiment-analysis
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


class SubredditAnalyzer():
    """Given a Mongodb database instance we are able to run sentiment analysis
    to analyzing given reddit submissions and subreddits as well.

    Using this object we can get the results for the positivity and negativity
    of a given subreddit or submission."""


    def __init__(self, mongo_reddit_collection, language='english'):
        """Constructs a SubRedditAnalyzer object."""

        """MongDB collection that we will be pulling our reddit data from.

        The database must have the following fielding fields in it:
            body, created_at, distinguished, edited, id, is_submitter
            link_id, parent_id, replies, score, stickied, submission
            subreddit, sorting_type."""
        self.__reddit_collection = mongo_reddit_collection

        """This is an out of the box Sentiment Analyzer model that is exceptionally good
        at analyzing social media data. We will feed individual comments to it and it will
        give us a score of polarity (positivity, negativity, neutral, and Compound)."""
        self.__comment_sentiment_analyzer = SentimentIntensityAnalyzer()

        """RedditPreprocessor that is used for preprocessing all of the comments that we will be
        analyzing. This object can later be configured by the user, in the event that they want
        edit their stop_word list, or change it's language."""
        self.__comment_preprocessor = RedditPreprocessor(self.__reddit_collection)

        """There are the options that a user can use as a sorting type.
        Anything else will trigger an error, if it is not in our set."""
        self.__valid_sorting_types = {'new', 'top', 'hot', None}


    # PRIVATE METHODS__________________________________________________________________________________


    def __check_analysis_paramters_are_valid_raise_exception(self, sorting_type_option,
                                                             max_number_of_comments_option=None,
                                                             max_number_of_submissions_option=None):
        """(Helper method)\n
        Method used to Make sure that the paramters passed to our analysis methods are valid.
        If the are not valid, then we throw an exception for the specific issue.\n

        Arguments:\n
            sorting_type_option {str or None} -- The sorting method that the user wants
                                                 to use to query data.
            
            max_number_of_comments_option {int} -- Represents the amount of comments to query.
                                                   We need to make sure it of a valid length.
            
            max_number_of_submissions_option {int} -- Represents the max number of submissions that
                                                      will be analyzed. We need to make sure it is
                                                      in a certain range.

        Raises:\n
            ValueError: When sorting type is not valid.\n
            ValueError: When max_number_of_comments_option is negative.\n
            ValueError: When max_number_of_submissions_option is negative."""

        if sorting_type_option not in self.__valid_sorting_types:
            raise ValueError(f"Error: sorting type must be of the following options: "
                             "{self.__valid_sorting_types}.")
    
        if max_number_of_comments_option and max_number_of_comments_option < 0:
            raise ValueError('max_number_of_comments_to_analyze must be a positivity.')

        if max_number_of_submissions_option and max_number_of_submissions_option < 0:
            raise ValueError('max_number_of_submissions_to_analyze must be a positivity.')


    # PUBLIC INTERFACE_________________________________________________________________________________


    def analyze_submission(self, submission_id, sorting_type=None,
                           display_all_comment_results=False,
                           max_number_of_comments_to_analyze=0):
        """Returns a dictionary containing the positivity and negativity of a submission.

        Arguments:\n
            submission_id {str} -- The reddit submission id of the submission you want to analyze.

        Keyword Arguments:\n
            sorting_type {str} -- Determines the type of comments you want to parse.
                                  Must be one of the following: 'hot', 'top', or 'new'
                                  (None is valid as well) (default: {None})\n
            display_all_comment_results {bool} -- True if user wants to seethe analysis results of each
                                                  comment; False otherwise. (default: {False})\n
            max_number_of_comments_to_analyze {int} -- This is the max amount of comments that we want to
                                                       analyze for a given submission.
                                                       A value of 0 means that we will collect all comments.
                                                       (default: {0})

        Returns:\n
            dict -- A dictionary in the form of {'positive': int_value, 'negative', int value}"""

        # Before we do anything, we want to make sure that the values that the user
        # Passed in are valid, otherwise we need to trigger an error, before doing
        # a bunch of time costly analysis.
        self.__check_analysis_paramters_are_valid_raise_exception(sorting_type,
                                                                  max_number_of_comments_to_analyze)

        preprocessed_submission_comments = \
            self.__comment_preprocessor.get_preprocessed_comments(submission_id,
                                                                  max_number_of_comments_to_analyze,
                                                                  sorting_type=sorting_type)

        # Used to sum up and get averages for positive and negative comments.
        positive_comment_results = []
        negative_comment_results = []

        for comment in preprocessed_submission_comments:
            analysis_results_of_comment = \
                self.__comment_sentiment_analyzer.polarity_scores(comment)

            # Comment might not be positive or negative, so by default it is ignored.
            # It will be set later if we find the comment to be positive or negative.
            classification_to_print_out = "Ignored"

            if(             
                # Concluded comment is positive.
                analysis_results_of_comment['compound'] >= 0.05 or \
                analysis_results_of_comment['neg'] == 0 and analysis_results_of_comment['pos'] > 0
            ):
                positive_comment_results.append(analysis_results_of_comment['compound'])
                classification_to_print_out = "Positive"
            elif(
                # Concluded comment is negative.
                analysis_results_of_comment['compound'] <= -0.05 or \
                analysis_results_of_comment['pos'] == 0 and analysis_results_of_comment['neg'] > 0
            ):
                negative_comment_results.append(abs(analysis_results_of_comment['compound']))
                classification_to_print_out = "Negative"

            if display_all_comment_results:
                # We want the user to know what subreddit a submission is from, since
                # we are running analysis on it and wanna make a neat little image.
                try:
                    subreddit_name = self.__reddit_collection.find_one({'submission': submission_id}
                                                                       )['subreddit_name']
                except CursorNotFound:
                    # Might not have a subreddit_name as a field for this one, so we
                    # Need a default label for this sort of situation.
                    subreddit_name = "NONE"

                # Now we can actually...show the results the user wants to see.
                print("\nSubreddit Name:", subreddit_name)
                print("Comment:", comment)
                print(f"Positivity Rating: {analysis_results_of_comment['pos']}")
                print(f"Negativity Results: {analysis_results_of_comment['neg']}")
                print(f"Neutral results: {analysis_results_of_comment['neu']}")
                print("Classification:", classification_to_print_out)

        # Need this to later get percentages of negativity and positivity (math stuffs).
        total_sum_of_result_scores = sum(positive_comment_results + negative_comment_results)

        # This implies we have not analyzed anthing.
        if total_sum_of_result_scores == 0:
            return {'positive': 0, 'negative': 0}

        average_positivity = sum(positive_comment_results) / total_sum_of_result_scores
        average_negativity = sum(negative_comment_results) / total_sum_of_result_scores

        # They also wanna see the final results of scoring (even tho they are returned).
        if display_all_comment_results:
            print(f'\nResults of all comments for submission: "{submission_id}"')
            print("Average Positivity: {:.2f}%".format(average_positivity * 100))
            print("Average Negativity: {:.2f}%".format(average_negativity * 100))

        return {'positive': average_positivity, 'negative': average_negativity}


    def analyze_subreddit(self, subreddit_name, sorting_type=None,
                          display_all_comment_results=False,
                          display_all_submission_results=False,
                          max_number_of_comments_to_analyze=0,
                          max_number_of_submissions_to_analyze=0):
        """Return a dictionary containing the positive and negative results of a given subreddit.

        Arguments:\n
            subreddit_name {str} -- The subreddit that we want to analyze.

        Keyword Arguments:\n
            sorting_type {str} -- The type of posts that we will grab. either 'hot', 'top', 'new'.
                                  (default: {None})\n
            display_all_comment_results {bool} -- True if user wants to display analysis results of
                                                  comments. (default: {False})\n
            display_all_submission_results {bool} -- True if user wants to display all analysis results
                                                     of each submission in the subreddit.
                                                     (default: {False})\n
            max_number_of_comments_to_analyze {int} -- The max number of comments that we will analyze
                                                       for positivity and negativity. (default: {0})\n
            max_number_of_submissions_to_analyze {int} -- The max number of submissions that we are
                                                          going to analyze for positivity and
                                                          negativity. (default: {0})\n

        Returns:\n
            dict -- Dictionary containing the positivity and negativity of a given subreddit.
                    {'positive': int, 'negative': int}"""

        # Before we do anything, we want to make sure that the values that the user
        # Passed in are valid, otherwise we need to trigger an error, before doing
        # a bunch of time costly analysis.
        self.__check_analysis_paramters_are_valid_raise_exception(sorting_type,
                                                                  max_number_of_comments_to_analyze,
                                                                  max_number_of_submissions_to_analyze)

        analysis_start_time = datetime.datetime.now()

        subreddit_submission_ids = []
        if sorting_type:
            # User only wants to get posts of given sorting type.
            subreddit_submission_ids = self.__reddit_collection.find({'subreddit_name': subreddit_name,
                                                                      'sorting_type': sorting_type}
                                                                     ).distinct('submission')
        else:
            # User did NOT give us a sorting type, so just grab everything.
            subreddit_submission_ids = self.__reddit_collection.find({'subreddit_name': subreddit_name}
                                                                     ).distinct('submission')

        # No posts found in subreddit, there is not point in analyzing, just return now.
        if len(subreddit_submission_ids) == 0:
            if display_all_comment_results or display_all_submission_results:
                print(f'No submissions were found for the subreddit {subreddit_name}.')
            return {'positive': 0, 'negative': 0}

        # We only want to grab the amount of submissions that the user wants us to,
        # so we need to make sure not to exceed the amount that exist.
        if(
            len(subreddit_submission_ids) > max_number_of_submissions_to_analyze and \
            max_number_of_submissions_to_analyze != 0
        ):
            # It is not zero, so we know that the user wants to get a subset of comments,
            # we just needed to make sure that we had enough in the first place.
            subreddit_submission_ids = subreddit_submission_ids[: max_number_of_submissions_to_analyze]

        # This will have records appended to it to keep track of positive and negative results.
        # later we will divide it by the amount of submissions we have. It will hold mean averages.
        average_results_for_subreddit = {'positive': 0, 'negative': 0}

        for submission_id in subreddit_submission_ids:
            # Dict with all averages of a submission in given subreddit.
            analysis_results_of_submission = \
                self.analyze_submission(submission_id, sorting_type=sorting_type,
                                        display_all_comment_results=display_all_comment_results,
                                        max_number_of_comments_to_analyze=\
                                            max_number_of_comments_to_analyze)

            average_results_for_subreddit['positive'] += analysis_results_of_submission['positive']
            average_results_for_subreddit['negative'] += analysis_results_of_submission['negative']

            # They want to see the rating for each submission post over time.
            if display_all_submission_results:
                print(f'Subreddit: {subreddit_name}:')
                print(f'Submission_id: {submission_id}:')
                print(f"Positivity Rating: {average_results_for_subreddit['positive']}")
                print(f"Negativity Rating: {average_results_for_subreddit['negative']}\n")

        analysis_end_time = datetime.datetime.now()

        # We can use this as our divisor in following calculations, so that we can
        # get average score for positivity and the average score for negativity.
        total_sum_of_all_submission_scores = average_results_for_subreddit['positive'] +\
                                             average_results_for_subreddit['negative']

        # We don't want to divide by zero.
        # We would get to this point if all results were evaluated as neutral in an odd case.
        if total_sum_of_all_submission_scores != 0:
            average_results_for_subreddit['positive'] /= total_sum_of_all_submission_scores
            average_results_for_subreddit['negative'] /= total_sum_of_all_submission_scores

        # They wanna show the averages in the method.
        if display_all_submission_results:
            print(f'\nResults of all comments for : "{subreddit_name}"')
            print("Average positivity: {:2f}%".format(average_results_for_subreddit['positive'] * 100))
            print("Average negativity: {:2f}%".format(average_results_for_subreddit['negative'] * 100))
            print(f"Total time: {analysis_end_time - analysis_start_time}")

        return average_results_for_subreddit


    def get_most_positive_subreddit_analysis_results(self, list_of_subreddits, sorting_type=None,
                                                     max_number_of_comments_to_analyze=0,
                                                     max_number_submissions_to_analyze=0):
        """Return a dict containing the subreddit with the most positive results, the positivity level,
           of the result, the negativity level of the results.

        Arguments:\n
            list_of_subreddits {list} -- List containing the subreddits that we will choose from to find
                                         the most positive.

        Keyword Arguments:\n
            sorting_type {str} -- The sorting type we will analyze our subreddit to find.
                                  Must be 'new', 'hot', or 'top' (default: {None})\n
            max_number_of_comments_to_analyze {int} -- The max number of comments that we will
                                                       analyze. 0 means we will query everything. (default: {0})\n
            max_number_submissions_to_analyze {int} -- The max number of submissions that we will analyze.
                                                       0 Means we will query everything. (default: {0})\n

        Returns:\n
            dict -- dict in the form {'subreddit': str, 'positive': int, 'negative': int}."""

        most_positive_subreddit = ""
        most_positive_subreddit = {}
        
        for subreddit in list_of_subreddits:
            analysis_result = self.analyze_subreddit(subreddit, max_number_of_comments_to_analyze=\
                                                                    max_number_of_comments_to_analyze,
                                                    max_number_of_submissions_to_analyze=\
                                                        max_number_submissions_to_analyze,
                                                    sorting_type=sorting_type)

            if analysis_result['positive'] > most_positive_subreddit['positive']:
                most_positive_subreddit = analysis_result
                most_positive_score = analysis_result['positive']

        most_positive_score['subreddit'] = subreddit
        return most_positive_score


    def get_most_negative_subreddit_analysis_results(self, list_of_subreddits, sorting_type=None,
                                                     max_number_of_comments_to_analyze=0,
                                                     max_number_submissions_to_analyze=0):
        """Return a dict containing the subreddit with the most negative results, the positivity level,
           of the result, the negativity level of the results.

        Arguments:\n
            list_of_subreddits {list} -- List containing the subreddits that we will choose from to find
                                         the most positive.

        Keyword Arguments:\n
            sorting_type {str} -- The sorting type we will analyze our subreddit to find.
                                  Must be 'new', 'hot', or 'top' (default: {None})\n
            max_number_of_comments_to_analyze {int} -- The max number of comments that we will
                                                       analyze. 0 means we will query everything. (default: {0})\n
            max_number_submissions_to_analyze {int} -- The max number of submissions that we will analyze.
                                                       0 Means we will query everything. (default: {0})\n

        Returns:\n
            dict -- dict in the form {'subreddit': str, 'positive': int, 'negative': int}."""

        most_negative_subreddit = ""
        most_negative_subreddit = {}
        
        for subreddit in list_of_subreddits:
            analysis_result = self.analyze_subreddit(subreddit, max_number_of_comments_to_analyze=\
                                                                    max_number_of_comments_to_analyze,
                                                    max_number_of_submissions_to_analyze=\
                                                        max_number_submissions_to_analyze,
                                                    sorting_type=sorting_type)

            if analysis_result['negative'] > most_negative_subreddit['negative']:
                most_negative_subreddit = analysis_result
                most_negative_score = analysis_result['negative']

        most_positive_score['subreddit'] = subreddit
        return most_negative_score


    # Later, once I implement word bubble and freq analysis.
    def show_hotest_submission_topics(self, submission_id):
        pass


    # Later, once I implement word bubble and freq analysis.
    def show_hotest_subreddit_topics(self, subreddit_id):
        pass
