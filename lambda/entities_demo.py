# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import logging
from typing import List

import ask_sdk_core.utils as ask_utils
import requests
from ask_sdk_core.dispatch_components import AbstractExceptionHandler, AbstractRequestHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_model import Response
from ask_sdk_model.slot import Slot
from ask_sdk_model.slu.entityresolution.resolution import Resolution
from ask_sdk_model.slu.entityresolution.status_code import StatusCode

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Welcome, ask me about a country."

        return (
            handler_input.response_builder
                         .speak(speak_output)
                         .ask(speak_output)
                         .response
        )


def get_slot_resolutions(slot):
    # type: (Slot | None) -> List[Resolution] | None
    if (slot is None or
            slot.resolutions is None or
            slot.resolutions.resolutions_per_authority is None):
        return None

    return [resolution for resolution in slot.resolutions.resolutions_per_authority if
            resolution.authority == "AlexaEntities" and resolution.status.code == StatusCode.ER_SUCCESS_MATCH]


class CountryKnowledgeIntentHandler(AbstractRequestHandler):
    """Handler for Country Knowledge Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("CountryKnowledgeIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        api_access_token = ask_utils.get_api_access_token(handler_input)
        slot = ask_utils.get_slot(handler_input, "country")
        resolutions = get_slot_resolutions(slot)

        if resolutions:
            resolved_entity = resolutions[0].values[0].value.id
            headers = {
                "Authorization": f"Bearer {api_access_token}",
                "Accept-Language": ask_utils.get_locale(handler_input)
            }
            response = requests.get(resolved_entity, headers=headers)

            if response.status_code == 200:
                entity = response.json()
                logger.info(entity)
                if "capital" in entity and "politicalLeader" in entity:
                    country = entity["name"][0]["@value"]
                    city = entity["capital"][0]["name"][0]["@value"]
                    person = entity["politicalLeader"][0]["name"][0]["@value"]
                    return (
                        handler_input.response_builder
                                     .speak(f"{country}'s political leader is {person}. Its capital city is {city}.")
                                     .ask("Ask me about another country.")
                                     .response
                    )

        return (
            handler_input.response_builder
                         .speak("Sorry, I\'m not sure about that.")
                         .ask("Ask me about another country")
                         .response
        )


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "You can ask me about any country! How can I help?"

        return (
            handler_input.response_builder
                         .speak(speak_output)
                         .ask(speak_output)
                         .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Goodbye!"

        return (
            handler_input.response_builder
                         .speak(speak_output)
                         .response
        )


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        # Any cleanup logic goes here.

        return handler_input.response_builder.response


class IntentReflectorHandler(AbstractRequestHandler):
    """The intent reflector is used for interaction model testing and debugging.
    It will simply repeat the intent the user said. You can create custom handlers
    for your intents by defining them above, then also adding them to the request
    handler chain below.
    """

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = f"You just triggered {intent_name}."

        return (
            handler_input.response_builder
                         .speak(speak_output)
            #            .ask("add a reprompt if you want to keep the session open for the user to respond")
                         .response
        )


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """

    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        speak_output = "Sorry, I had trouble doing what you asked. Please try again."

        return (
            handler_input.response_builder
                         .speak(speak_output)
                         .ask(speak_output)
                         .response
        )


# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.

sb = SkillBuilder()

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(CountryKnowledgeIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
# make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers
sb.add_request_handler(IntentReflectorHandler())

sb.add_exception_handler(CatchAllExceptionHandler())

handler = sb.lambda_handler()
