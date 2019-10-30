import requests
import json
import re
import threading
import datetime
from urllib.parse import unquote
from requests_aws4auth import AWS4Auth
from threading import Thread

receiver = "your email id"

# ------ Bot Credentials--------------
username = "bot email id hosted on the organization's server"
password = "password"
botDetails = json.dumps({
    "UserAgent": "Test Bot V1",
    "EndpointId": "endpoint random generated",
    "Culture": "en-US"
})
# ------ Bot Credentials--------------

# ------ AWS Credentials--------------
awsLexUrl = "api gateway url for lex bot" 
awsAccessId = "access id"
awsAccessKey = "access key"
awsRegion = "region"
awsService = "lex"
# ------ AWS Credentials--------------

# -----------------Global Variables--------------------
globalUrl = "connection url for skype for business on organization server"
nextAckEventUrl = ""
accessToken = ""
# convoData = {}
# -----------------Global Variables---------------------

# AUTHENTICATION
def authentication(globalUrl, username, password):
    authUrl = globalUrl + "/WebTicket/oauthtoken"
    authHeaders = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    authBody = "grant_type=password&username=" + username + "&password=" + password
    authResponse = requests.post(url=authUrl, data=authBody, headers=authHeaders)
    print("Getting access token")
    print("Status: ", authResponse.status_code)
    authString = authResponse.content.decode()
    authJson = json.loads(authString)
    token = authJson['access_token']
    print("access token: ", token)
    global accessToken
    accessToken = token


# CREATING AN APPLICATION
def create_application(globalUrl, botDetails):
    createAppUrl = globalUrl + "/ucwa/oauth/v1/applications"
    createAppHeaders = {
        "Authorization": "Bearer " + accessToken,
        "Content-Type": "application/json"
    }
    createAppBody = botDetails
    createAppResponse = requests.post(url=createAppUrl, data=createAppBody, headers=createAppHeaders)
    print("Creating Application")
    print("Status: ", createAppResponse.status_code)
    if createAppResponse.status_code == 404:
        # generate new access token
        authentication(globalUrl, username, password)
        create_application(globalUrl, botDetails)
    createAppString = createAppResponse.content.decode()
    createAppJson = json.loads(createAppString)
    print("Create Application Response: ", createAppJson)
    return createAppJson


# MAKE BOT ONLINE
def make_bot_online(globalUrl, applicationId):
    makeBotOnlineUrl = globalUrl + "/ucwa/oauth/v1/applications/" + applicationId + "/me/makeMeAvailable"
    makeBotOnlineHeaders = {
        "Authorization": "Bearer " + accessToken,
        "Content-Type": "application/json"
    }
    makeBotOnlineBody = json.dumps({
        "SupportedModalities": ["Messaging"],
        "supportedMessageFormats": ["Plain", "Html"]
    })
    makeBotOnlineResponse = requests.post(url=makeBotOnlineUrl, data=makeBotOnlineBody, headers=makeBotOnlineHeaders)
    print("Making Bot Online")
    print("Status: ", makeBotOnlineResponse.status_code)


# KEEP THE BOT ALIVE BY REPORTING THE ACTIVITY EVERY 1 MINUTES
def keep_bot_online(globalUrl, applicationId):
    keepBotOnlineUrl = globalUrl + "/ucwa/oauth/v1/applications/" + applicationId + "/reportMyActivity"
    keepBotOnlineHeaders = {
        "Authorization": "Bearer " + accessToken,
        "Content-Type": "application/json"
    }
    keepBotOnlineResponse = requests.post(url=keepBotOnlineUrl, headers=keepBotOnlineHeaders)
    print("Status: ", keepBotOnlineResponse.status_code)
    if keepBotOnlineResponse.status_code == 401:
        print("Access Token expired.")
        authentication(globalUrl, username, password)
        create_application(globalUrl, botDetails)
        make_bot_online(globalUrl, applicationId)
    if keepBotOnlineResponse.status_code == 404:
        print("Bot is now OFFLINE.")
        create_application(globalUrl, botDetails)
        make_bot_online(globalUrl, applicationId)
    elif keepBotOnlineResponse.status_code == 204:
        print("Bot is ONLINE ", datetime.datetime.now().time())
    threading.Timer(60.0, keep_bot_online, [globalUrl, applicationId]).start()


# START CONVERSATION
def start_convo(globalUrl, applicationId, receiver):
    startConvoUrl = globalUrl + "/ucwa/oauth/v1/applications/" + applicationId + "/communication/messagingInvitations"
    startConvoHeaders = {
        "Authorization": "Bearer " + accessToken,
        "Content-Type": "application/json"
    }
    startConvoBody = json.dumps({
        "importance": "Normal",
        "sessionContext": "43dc0ef6-0570-4467-bb7e-49fcbea8e945",
        "subject": "Testing subject 1",
        "telemetryId": None,
        "to": "sip:" + receiver,
        "operationId": "319e45184b7136d6d69fa6573011e9b2"
    })
    print("Starting a Conversation with " + receiver)
    startConvoResponse = requests.post(url=startConvoUrl, data=startConvoBody, headers=startConvoHeaders)
    print("Status: ", startConvoResponse.status_code)


# GET MESSAGES
def get_messages(globalUrl, applicationId, nextEventUrl):
    if nextEventUrl == "":
        getMessageUrl = globalUrl + "/ucwa/oauth/v1/applications/" + applicationId + "/events?ack=1"
    else:
        getMessageUrl = globalUrl + nextEventUrl
    getMessageHeaders = {
        "Authorization": "Bearer " + accessToken
    }
    getMessageResponse = requests.get(url=getMessageUrl, headers=getMessageHeaders)
    print("Getting Messages")
    print("Status: ", getMessageResponse.status_code)
    getMessageString = getMessageResponse.content.decode()
    getMessageJson = json.loads(getMessageString)
    print("Get Messages Response: ", getMessageJson)
    return getMessageJson


# SEND MESSAGE
def send_message(globalUrl, applicationId, convoId, messageText):
    # SENDING A MESSAGE

    sendMessageUrl = globalUrl + "/ucwa/oauth/v1/applications/" + applicationId + "/communication/conversations/" + convoId + "/messaging/messages"
    sendMessageHeaders = {
        "Authorization": "Bearer " + accessToken,
        "Content-Type": "text/plain"
    }
    if type(messageText) == str:
        sendMessageBody = messageText.encode('utf-8')
        print("Sending Message")
        sendMessageResponse = requests.post(url=sendMessageUrl, data=sendMessageBody, headers=sendMessageHeaders)
        print("Status: ", sendMessageResponse.status_code)
    else:
        for entry in messageText:
            sendMessageBody = entry.encode('utf-8')
            print("Sending Message")
            sendMessageResponse = requests.post(url=sendMessageUrl, data=sendMessageBody, headers=sendMessageHeaders)
            print("Status: ", sendMessageResponse.status_code)


    return


# GET CONVERSATION ID
def getConvoId(getMessages):
    for entry in getMessages['sender']:
        if entry['rel'] == "conversation":
            return entry['href'].split("conversations/")[1]


# GET BOT PRESENCE
def getPresence(applicationId):
    getPresenceUrl = globalUrl + "/ucwa/oauth/v1/applications/" + applicationId + "/me/presence"
    getPresenceHeaders = {
        "Authorization": "Bearer " + accessToken
    }
    getPresenceResponse = requests.get(url=getPresenceUrl, headers=getPresenceHeaders)
    if getPresenceResponse.status_code == 200:
        getPresenceString = getPresenceResponse.content.decode()
        getPresenceJson = json.loads(getPresenceString)
        if getPresenceJson["availability"] == "Online":
            botPresence = "Online"
        else:
            botPresence = getPresenceJson["availability"]
    else:
        botPresence = "Offline"
    return botPresence


# ACCEPT THE INCOMING CONVERSATION REQUESTS
def accept_convo(globalUrl, applicationId):
    if nextAckEventUrl == "":
        getMessageUrl = globalUrl + "/ucwa/oauth/v1/applications/" + applicationId + "/events?ack=1"
    else:
        getMessageUrl = globalUrl + nextAckEventUrl
    getMessageHeaders = {
        "Authorization": "Bearer " + accessToken
    }
    getMessageResponse = requests.get(url=getMessageUrl, headers=getMessageHeaders)
    getMessageString = getMessageResponse.content.decode()
    getMessageJson = json.loads(getMessageString)

    # check here if any conversation request is there or not
    try:
        for outer in getMessageJson['sender']:
            for inner in outer['events']:
                try:
                    if inner['_embedded']['messagingInvitation']['direction'] == "Incoming":
                        try:
                            acceptUrl = globalUrl + inner['_embedded']['messagingInvitation']['_links']['accept']['href']
                            acceptConvoResponse = requests.post(url=acceptUrl, headers=getMessageHeaders)
                            if acceptConvoResponse.status_code == 204:
                                print("Conversation Accepted")
                                convoId = \
                                inner['_embedded']['messagingInvitation']['_links']['messaging']['href'].split("conversations/")[1].split("/")[
                                    0]
                                userName = inner['_embedded']['messagingInvitation']['_embedded']['from']['name']
                                userMessageText = inner['_embedded']['messagingInvitation']['_links']['message']['href'].split(",")[1]
                                userEmailId = inner['_embedded']['messagingInvitation']['_embedded']['from']['uri'].split(":")[1]
                                if "+" in userMessageText:
                                    userMessageText = userMessageText.replace("+", " ")
                                    print("Input from New User: ", userMessageText)
                                tempDict = {"convoId": convoId, "userName": userName, "userMessageText": userMessageText, "userEmailId": userEmailId}
                                # Create a new unique thread here for every incoming conversation request

                                try:
                                    chatThread = Thread(target=chatting, args=(convoId, ))  # making a new thread for each user for chatting
                                    print("Starting a new thread")
                                    chatThread.start()
                                    # chatting("", convoData)  # access global convodata automatically
                                except Exception as e:
                                    print("Error in Chatting thread: ",e)
                                    chatThread = Thread(target=chatting, args=(convoId, ))  # making a new thread for each user for chatting
                                    print("Starting a new thread")
                                    chatThread.start()

                        except Exception:
                            print("No new request")

                except Exception:
                    # Do nothing
                    temp = 1
    except Exception:
        print("There is no new sender")
        botPresence = getPresence(applicationId)
        if botPresence == "Offline":
            create_application(globalUrl, botDetails)
            make_bot_online(globalUrl, applicationId)
    threading.Timer(1.0, accept_convo, [globalUrl, applicationId]).start()


# SEND USER MESSAGE TO LEX
def sendToLex(userMessage):
    try:
        awsAuth = AWS4Auth(awsAccessId, awsAccessKey, awsRegion, awsService)
        body = json.dumps({
            "inputText": userMessage
        })
        awsResponse = requests.post(url=awsLexUrl, auth=awsAuth, data=body)
        if awsResponse.status_code == 200:
            awsResponseString = awsResponse.content.decode()
            awsResponseJson = json.loads(awsResponseString)
            replyFromLex = awsResponseJson["message"]
            print("Reply: ", replyFromLex)
        else:
            replyFromLex = awsResponse.status_code + " error in sending response to lex"
        return replyFromLex
    except Exception as e:
        return e


# START A CHATTING THREAD BETWEEN USER AND BOT
def chatting(convoId):
    global nextAckEventUrl
    getMessageJson = get_messages(globalUrl, applicationId, nextAckEventUrl)

    try:
        # IF THERE WAS A RESYNC IN PREVIOUS GET, THEN PROCESS USER RESPONSE FROM THE NEXT GETMESSAGEJSON
        if "resync" in getMessageJson['_links']:
            nextAckEventUrl = getMessageJson['_links']['resync']['href']  # getting the resync event url
            newGetMessageJson = get_messages(globalUrl, applicationId, nextAckEventUrl)  # hitting get messages again with resync url
            nextAckEventUrl = newGetMessageJson['_links']['next']['href']  # SETTING THE NEXT EVENT URL GLOBALLY
            try:
                for outer in newGetMessageJson['sender']:
                    try:
                        for inner in outer['events']:
                            try:
                                if inner['_embedded']['message']['direction'] == "Incoming":
                                    if inner['_embedded']['message']['_links']['self']['href'].split("conversations/")[1].split("/")[0] == convoId:
                                        userMessageEncoded = inner['_embedded']['message']['_links']['htmlMessage']['href'].split(",")[1]
                                        userMessageHtml = unquote(userMessageEncoded)
                                        userMessageText = re.sub(re.compile('<.*?>'), '', userMessageHtml)
                                        if "+" in userMessageText:
                                            userMessageText = userMessageText.replace("+", " ")
                                            print("User Input: ", userMessageText)
                                        else:
                                            print("User Input: ", userMessageText)
                                        try:
                                            print("Sending input to Lex")
                                            replyFromLex = sendToLex(
                                                userMessageText)  # if some user message is found, then send that to lex and process further
                                            print("replyFromLex: ", replyFromLex)
                                            print("Sending message back to user")
                                            send_message(globalUrl, applicationId, convoId, replyFromLex)
                                            chatting(convoId)  # calling the same function in recursion
                                        except Exception as e:
                                            print("Error occured while conversing with lex ", e)
                            except Exception as e:
                                print("Going forward in inner loop")

                    except Exception as e:
                        print("Going forward in outer loop")

            except Exception as err:
                print("No user input ")
                chatting(convoId)  # calling the same function in recursion
        else:
            nextAckEventUrl = getMessageJson['_links']['next']['href']  # SETTING THE NEXT EVENT URL GLOBALLY

        # CHECKING FOR USER MESSAGES
        try:
            for outer in getMessageJson['sender']:
                try:
                    for inner in outer['events']:
                        try:
                            if inner['_embedded']['message']['direction'] == "Incoming":
                                if inner['_embedded']['message']['_links']['self']['href'].split("conversations/")[1].split("/")[0] == convoId:
                                    userMessageEncoded = inner['_embedded']['message']['_links']['htmlMessage']['href'].split(",")[1]
                                    userMessageHtml = unquote(userMessageEncoded)
                                    userMessageText = re.sub(re.compile('<.*?>'), '', userMessageHtml)
                                    if "+" in userMessageText:
                                        userMessageText = userMessageText.replace("+", " ")
                                        print("User Input: ", userMessageText)
                                    else:
                                        print("User Input: ", userMessageText)

                                    try:
                                        print("Sending input to Lex")
                                        replyFromLex = sendToLex(
                                            userMessageText)  # if some user message is found, then send that to lex and process further
                                        print("replyFromLex: ", replyFromLex)
                                        print("Sending message back to user")
                                        send_message(globalUrl, applicationId, convoId, replyFromLex)
                                        chatting(convoId)  # calling the same function in recursion
                                    except Exception as e:
                                        print("Error occured while conversing with lex ", e)
                        except Exception as e:
                            print("Going forward in inner loop")

                except Exception as e:
                    print("Going forward in outer loop")

        except Exception as err:
            print("No user input ")
            chatting(convoId)  # calling the same function in recursion
        # threading.Timer(1.0,chatting).start()

        chatting(convoId)  # calling the same function again after complete execution

    except Exception as e:
        print("Error in main chatting thread ", e)
        chatting(convoId)


# ------------FLOW STARTS-------------------

authentication(globalUrl, username, password)  # Step1
createAppJson = create_application(globalUrl, botDetails)  # Step2

applicationId = re.findall('\d+', createAppJson['_links']['self']['href'])[1]

make_bot_online(globalUrl, applicationId)  # Step3

keep_bot_online(globalUrl, applicationId)  # Step 4 ... KEEPING BOT ONLINE (PARALLEL THREAD)

accept_convo(globalUrl,
             applicationId)  # Checking for incoming conversations and accepting it. Incomming conversations are stored in convoData (PARALLEL THREAD)

# start_convo(globalUrl, applicationId, receiver)  # Step5
#
# getMessages = get_messages(globalUrl, applicationId, "")  # Step6
#
# convoId = getConvoId(getMessages)   # Step7

#
# # It should listen to incoming messages after every action through the "next" element in the json. The program should listen to that url for a
# # specefic time before proceeding with another send IM call
