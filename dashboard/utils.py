class UserData:
    def __init__(self, username, photo, image, image_filename, user_caption, generated_caption, feedback, score): # generated caption?
        ''' 
        username: string
        image: image file
        image_filename: string
        user_caption: string
        generated_caption: string
        feedback: string
        score: float
        '''
        self.username = username
        self.photo = photo
        self.image = image
        self.image_filename = image_filename
        self.user_caption = user_caption
        self.generated_caption = generated_caption
        self.feedback = feedback
        self.score = score

    def getScore(self):
        return self.score

    def getFeedback(self):
        return self.feedback

class User:
    def __init__(self,username, data, score=0):
        ''' 
        username: string
        data: list of UserData
        totalScore: float
        '''
        self.username = username
        self.data = data
        self.score = self.get_score(data)
    
    def get_score(self,data):
        score = 0
        for obs in data:
            score += obs.score
        return score

    def update_score(self,amount):
        self.score+=amount

    def getUsername(self):
        return self.username
    
    # returns a list of UserData objects corresponding to user
    def getObservations(self):
        return self.data
    def addObservation(self, userdata):
        self.data.append(userdata)