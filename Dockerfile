FROM python
ADD . .
RUN pip install numpy pandas openpyxl Pillow scikit-image opencv-python-headless selenium webdriver-manager tkintertable
