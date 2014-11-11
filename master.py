from flask import Flask, render_template, redirect, request, session as websession
from model import PlaySession, dbsession
import pandas as pd 
from sklearn.ensemble import RandomForestClassifier
from universals import data_dict, reversed_data_dict , column_order


app = Flask(__name__)
app.secret_key = 'PredictionFTW'

forest = RandomForestClassifier(n_estimators = 100)

df = pd.read_csv('data cleaning and imputing/imputed.csv', header=0)

# removing first column because it's duplicative - it's just the index column and pandas will assign that again anyway
df = df.ix[:,1:]


@app.route("/")
def index():
    return render_template('seed_questions.html')

@app.route("/religious", methods = ["POST"])
def first_question():
	global data_dict, reversed_data_dict, forest, df

	age = int(request.form.get("age"))
	sex = data_dict['sex'][str(request.form.get("sex"))]
	race = data_dict['race'][str(request.form.get("race"))]
	region = data_dict['region'][str(request.form.get("region"))]
	highest_grade = int(request.form.get("highest-grade"))
	employment_status = data_dict['employment_status'][str(request.form.get("employment-status"))]
	marital_status = data_dict['marital_status'][str(request.form.get("marital-status"))]

	column_of_var = 8

	train_data = df.ix[:,0:column_of_var] #trimming it down to just the columns up to and including the target variable

	train_data_values = train_data.values #converting out of dataframe

	features_of_training_data = train_data_values[0::,0:-1:] #whole dataset minus last column, which is target variable
	target_variable = train_data_values[0::,-1] # slices off the last column, which is the target variable 

	# # Fit the training data to the target and create the decision trees
	forest = forest.fit(features_of_training_data, target_variable)

	test_data = [age, sex, race, region, highest_grade, employment_status, marital_status]

	# # Take the same decision trees and run it on the test data
	predicted_religious = forest.predict(test_data)[0] #comes back as a one-item list.  sliced it down to a single number

	playsession = PlaySession(age = age, sex = sex, race = race, region = region, highest_grade = highest_grade, employment_status = employment_status, marital_status = marital_status, predicted_religious = predicted_religious)

	playsession.add_play_session()

	websession['session_id'] = playsession.session_id
	websession['current_q_numb'] = 0
	
	predicted_religious_translated = reversed_data_dict['religious'][int(predicted_religious)]


	return render_template('religious.html',  predicted_religious_translated = predicted_religious_translated)


@app.route("/nextquestion", methods = ["POST"])
def next_question():
	global data_dict, reversed_data_dict, forest, df, column_order

	old_question_var_name = column_order[websession['current_q_numb']]
	new_question_var_name = column_order[websession['current_q_numb']+1]
	new_question_html = str(new_question_var_name) + ".html"
	
	old_question_answer = data_dict[old_question_var_name][str(request.form.get(old_question_var_name))]
	column_of_var = column_order.index(new_question_var_name) + 8 #because there are 7 demographic questions before the predictable questions begin, and we need to slice up to current column plus one b/c range of slice is not inclusive

	### Set up training data ###
	train_data = df.ix[:,0:column_of_var] #trimming it down to just the columns up to and including the target variable
	train_data_values = train_data.values #converting out of dataframe
	features_of_training_data = train_data_values[0::,0:-1:] #whole dataset minus last column, which is target variable
	target_variable = train_data_values[0::,-1] # slices off the last column, which is the target variable 

	# Fit the training data to the target and create the decision trees
	forest = forest.fit(features_of_training_data, target_variable)

	# Get current playsession object out of database, using id stored in websession
	playsession = dbsession.query(PlaySession).get(websession['session_id'])

	setattr(playsession, old_question_var_name, old_question_answer)

	# Set up test data  ## PROB AREA
	test_data = playsession.ordered_parameter() 


	predicted_new_question_answer = forest.predict(test_data)[0] #comes back as a one-item list.  sliced it down to a single number

	# add stated spiritual and predicted party to database, then commit

	setattr(playsession, new_question_var_name, predicted_new_question_answer)
	playsession.commit_play_session()

	predicted_new_question_translated = reversed_data_dict[new_question_var_name][int(predicted_new_question_answer)]

	websession['current_q_numb'] += 1

	return render_template(new_question_html, predicted_new_question_translated = predicted_new_question_translated)



if __name__ == "__main__":
    app.run(debug = True)