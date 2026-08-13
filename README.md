AgroSense — Crop and Fertilizer Recommendation System

AgroSense is a final year engineering project that combines IoT hardware and machine learning to help farmers in Nepal decide which crop to grow and which fertilizer to use based on real soil and environmental conditions. Instead of relying on guesswork or generic advice, AgroSense reads live data from sensors, runs it through trained machine learning models, and gives an instant recommendation.

What the System Does

The system takes soil nutrient levels (Nitrogen, Phosphorus, Potassium), temperature, humidity, soil moisture, soil pH, and rainfall as inputs. It first predicts the most suitable crop for those conditions, then uses that result to recommend the appropriate fertilizer. This two-step chained approach ensures the fertilizer recommendation is always linked to the predicted crop rather than being a separate and unrelated output.

How It Works

Sensors connected to an ESP32 microcontroller read temperature, humidity, and soil moisture automatically. Soil pH and nutrient values (NPK) are entered manually through the dashboard. Rainfall data is fetched automatically from the Open-Meteo weather API for the Pokhara region. All this data is sent from the ESP32 to a Flask backend server over WiFi, where the machine learning models process it and return a recommendation. The result is shown on a Streamlit web dashboard and also displayed on a small LCD screen attached to the ESP32 device itself.

Machine Learning Models

Four classification algorithms were trained and compared: Random Forest, Decision Tree, Support Vector Machine, and Naive Bayes. Random Forest was selected as the final model for both crop and fertilizer recommendation. For crop recommendation, the model was trained on 2,200 records covering 22 different crop types using seven input features. It achieved a test accuracy of 99.55% and a weighted F1-score of 0.9955. Stratified 5-fold cross validation was used during training to ensure the model generalizes well to unseen data, which is a stronger evaluation method than a simple single train-test split.

Hardware Used

The physical device consists of an ESP32 development board as the main microcontroller, a DHT22 sensor for reading temperature and humidity, a capacitive soil moisture sensor for reading soil water content, an analog pH probe for measuring soil acidity, and a 16x2 LCD screen for displaying the recommendation directly on the device. The system can be powered using a standard 5V adapter or a portable LiPo battery for use in the field.

Software and Tools

The entire software stack is open source and free to use. Python was used for all machine learning development. Scikit-learn was used to train and evaluate the models. Flask was used to build the backend API that serves the trained models. Streamlit was used to build the web dashboard. Joblib was used to save and load the trained model files. The ESP32 firmware was written in C++ using the Arduino framework.

Project Structure

The project is organized into four main parts. The notebooks folder contains the Jupyter notebooks used for training and evaluating the crop and fertilizer models. The models folder contains the saved model and label encoder files. The backend file runs the Flask API server. The dashboard file runs the Streamlit web interface.

How to Run the Project

First clone this repository and install the required Python packages listed in the requirements file. Then start the Flask API server, which will run locally on your machine. Next run the Streamlit dashboard, which will open in your browser. Enter your sensor readings or connect the ESP32 device to fetch them automatically, then click the recommendation button to get your crop and fertilizer prediction.

Limitations

The training datasets used in this project are sourced from Indian agricultural data and may not fully represent Nepal's soil conditions, rainfall patterns, and temperature profiles. The fertilizer dataset is also very small with only 99 records, so its model results should be treated with caution. Collection of Nepal-specific field data for retraining is planned as a follow-up to this project.

Future Plans

The immediate next step is to collect soil sample data from multiple districts in Nepal and retrain the models on locally relevant data. Additional plans include deploying the Flask API to a cloud server so the system can work over the internet rather than only on a local WiFi network, adding Nepali language support to the dashboard, and expanding the fertilizer dataset with more crop and soil combinations specific to Nepal.

Team

This project was developed by Sushovan, Akarshan Poudel, Kushal Neupane, and Sachin Kandel as a final year project for the Bachelor of Engineering in Computer Engineering at Pokhara University, School of Engineering.

License

This project is developed for academic purposes under Pokhara University and is not intended for commercial use.
