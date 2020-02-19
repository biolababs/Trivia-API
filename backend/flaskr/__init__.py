import os, random, sys, traceback
from flask import Flask, request, abort, jsonify, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

from models import *

# ----------------------------------------------------------------------
# Utils
# ----------------------------------------------------------------------

# Set up a function to paginate trivia questions with 10 results per page.
# Returns the list of 10 questions. 
QUESTIONS_PER_PAGE = 10

def paginate_questions(request, selection, page):
  if not page:
    page = request.args.get('page', 1, type=int)
  start = (page - 1) * QUESTIONS_PER_PAGE
  end = start + QUESTIONS_PER_PAGE

  questions = [question.format() for question in selection]
  questions_displayed = questions[start:end]

  return questions_displayed

# Set up function to validate if difficulty level is valid.

def is_valid_difficulty(difficulty):
  difficulty = int(difficulty)
  if difficulty >= 1 and difficulty <= 5:
    return True
  else:
    return False

# ----------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------

def create_app(test_config=None):
  # create and configure the app
  app = Flask(__name__)
  app.url_map.strict_slashes = False
  setup_db(app)

  # CORS app
  cors = CORS(app, resources={r"/api/*": {"origins": "*"}})

  # CORS Headers 
  @app.after_request
  def after_request(response):
      response.headers.add(
        'Access-Control-Allow-Headers',
        'Content-Type,Authorization,true'
      )
      response.headers.add(
        'Access-Control-Allow-Methods',
        'GET,PATCH,POST,DELETE,OPTIONS'
      )
      return response

# ----------------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------------

  # Endpoint to handle GET requests for all available categories.
  @app.route('/categories', methods=['GET'])
  def get_categories():
      categories = Category.query.all()
      if not categories:
        abort(404)

      return jsonify({
        'success': True,
        'categories': {category.id:category.type for category in categories},
      }), 200

  # Endpoint to handle GET requests for questions, paginated by QUESTIONS_PER_PAGE, showing all questions.
  @app.route('/questions', methods=['GET'])
  @app.route('/questions/<int:page>', methods=['GET'])
  def get_questions(page=False):
    # Get categories for JSON return for frontend.
    categories = Category.query.all()
    # Get all questions
    questions = Question.query.all()
    questions_displayed = paginate_questions(request, questions, page=page)
    if not questions_displayed:
      abort(404)

    return jsonify({
      'questions': questions_displayed,
      'categories': {category.id:category.type for category in categories},
      'success': True,
      'total_questions': len(questions),
      'next_url': url_for('get_questions', page=page+1)
      }), 200

  # Endpoint to handle GET request for questions, paginated by QUESTIONS_PER_PAGE and filtered by category ID.
  # Uses paginate_questions for the pagination.
  @app.route('/categories/<category>/questions', methods=['GET'])
  @app.route('/categories/<category>/questions/<int:page>', methods=['GET'])
  def get_questions_by_category(category, page=False):
    category_data = False

    # Checks for valid category ID.
    if category.isnumeric():
      category_data = Category.query.get(category)
      category_id = category

    # Checks for category type and converts to ID if found.
    if not category_data:
      category_data = Category.query.filter_by(type=category).first()
      category_id = category_data.id

    # If category is not found, returns error message.
    if not category_data:
      abort(400)

    questions = Question.query.filter_by(category=category_id).all()
    questions_displayed = paginate_questions(request, questions, page=page)

    # If page number doesn't exist, returns 404.
    if not questions_displayed:
      abort(404)

    return jsonify({
      'questions': questions_displayed,
      'success': True,
      'total_questions': len(questions),
      'next_url': url_for('get_questions_by_category', category=category, page=page+1)
      }), 200

  # Endpoint to handle DELETE requests using question ID.
  @app.route('/questions/<int:quest_id>', methods=['DELETE'])
  def delete_questions(quest_id):
    # Checks that question ID is not 0.
    if not quest_id:
      abort(400)

    question_to_delete = Question.query.get(quest_id)
    # Checks if question ID exists.
    if not question_to_delete:
      abort(404)

    try:
      question_to_delete.delete()
      db.session.commit()

    except:
      db.session.rollback()
      exc_type, exc_value, exc_traceback = sys.exc_info()

      print("*** print_exception:")
      traceback.print_exception(exc_type, exc_value, exc_traceback, limit = 2, file = sys.stdout)
      abort(500)

    return jsonify({
      'id': quest_id,
      'success': True
      }), 200

  # Endpoint to add new questions to the database.
  @app.route('/questions', methods=['POST'])
  def add_questions():
    body = request.get_json()

    # Checks for values for each required field, otherwise throws a 400.
    if 'question' not in body:
      abort(400)
    if 'answer' not in body:
      abort(400)
    if 'category' not in body:
      abort(400)
    if 'difficulty' not in body:
      abort(400)

    question = body['question']
    answer = body['answer']
    category = body['category']
    difficulty = body['difficulty']

    category_data = False
    # Checks for valid category ID.
    if isinstance(category, int) or category.isnumeric():
      category_data = Category.query.get(category)
      category_id = category

    # Checks for category type and converts to ID if found.
    if not category_data:
      category_data = Category.query.filter_by(type=category).first()
      category_id = category_data.id

    # If category is not found, returns error message.
    if not category_data:
      abort(400)

    if not is_valid_difficulty(difficulty):
      abort(422)

    new_question = Question(
      question = question,
      answer = answer,
      category = category_id,
      difficulty = difficulty
    )

    try:
      db.session.add(new_question)
      db.session.commit()
      data = {
        'id': new_question.id,
        'question': new_question.question,
        'answer': new_question.answer,
        'category': new_question.category,
        'difficulty': new_question.difficulty
      }

    except:
      db.session.rollback()
      exc_type, exc_value, exc_traceback = sys.exc_info()

      print("*** print_exception:")
      traceback.print_exception(exc_type, exc_value, exc_traceback, limit = 2, file = sys.stdout)
      abort(500)

    return jsonify({
      'question': data,
      'success': True
      }), 200

  # Endpoint to handle search requests.
  @app.route('/search', methods=['POST'])
  def find_questions():
    body = request.get_json()
    search_term = body['searchTerm']
    search_data = Question.query.filter(Question.question.ilike('%' + search_term + '%')).all()

    if not search_data:
      abort(404)

    return jsonify({
      'questions': [data.format() for data in search_data],
      'success': True,
      'totalQuestions': len(search_data)
    }), 200

  # Endpoint to play quiz that filters by category and previous questions that have been answered. 
  @app.route('/quizzes', methods=['POST'])
  def play_quiz():
    body = request.get_json()
    category = body['category']
    if isinstance(category, dict):
      category_id = int(category['id'])
    else:
      category_id = int(category)
    if 'previous_questions' in body:
      previous_questions = body['previous_questions']
    else:
      previous_questions = []

    questions = Question.query

    if category_id is not 0:
      quiz_category = Category.query.get(category_id)

      if not quiz_category:
        abort(404)

      questions = questions.filter_by(category=category_id)

    if previous_questions:
      questions = questions.filter(Question.id.notin_(previous_questions))
    questions = questions.all()
    if not questions:
      abort(404)

    return jsonify({
      'category': category,
      'previous_questions': previous_questions,
      'question': random.choice(questions).format(),
      'success': True
    }), 200

# ----------------------------------------------------------------------
# Error handlers
# ----------------------------------------------------------------------

  #Error handler for malformed requests.
  @app.errorhandler(400)
  def bad_request(error):
    return jsonify({
      "success": False, 
      "error": 400,
      "message": "Bad request."
      }), 400

  #Error handler for objects that cannot be found in the database.
  @app.errorhandler(404)
  def not_found(error):
    return jsonify({
      "success": False, 
      "error": 404,
      "message": "Item not found."
      }), 404

  #Error handler for requests that cannot be processed.
  @app.errorhandler(422)
  def unprocessable(error):
    return jsonify({
      "success": False, 
      "error": 422,
      "message": "Request could not be processed."
      }), 422

  #Error handler for when the server fails. 
  @app.errorhandler(500)
  def internal_server_error(error):
    return jsonify({
      "success": False, 
      "error": 500,
      "message": "Internal Server Error."
      }), 500

# ----------------------------------------------------------------------
# Runs app
# ----------------------------------------------------------------------

  return app