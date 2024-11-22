import json
from typing import List, Dict, Tuple, Union
from rtclient.models import ItemCreateMessage, SessionUpdateMessage, ToolsDefinition
from search import bing_web_search


class AssistantService:

    def __init__(self):
        self.language = "Hindi"
        self.tools_for_generic_assistants = [
            {
                'name': 'get_weather',
                'description': 'get the weather of the location',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'location': {'type': 'string', 'description': 'location for the weather'}
                    }
                },
                'returns': lambda arg: f"the weather of {json.loads(arg)['location']} is 40F and rainy"
            },
            {
                'name': 'Assistant_MobileAssistant',
                'description': 'Help user to answer mobile related questions, such as billing, contract, etc.',
                'parameters': {'type': 'object', 'properties': {}},
                'returns': lambda arg: "Assistant_MobileAssistant"
            },
            {
                'name': 'Assistant_ShopAssistant',
                'description': 'Help user to answer shop-related questions, such as shop location, available time, etc.',
                'parameters': {'type': 'object', 'properties': {}},
                'returns': lambda arg: "Assistant_ShopAssistant"
            },
            {
                'name': 'search_generic_information',
                'description': 'Use this function to search for generic information. Do not tell customers fake billing information before getting a result.',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'query': {'type': 'string', 'description': 'query'}
                    }
                },
                'returns': lambda arg: bing_web_search(json.loads(arg)['query'])
            }
        ]

        self.tools_for_mobile_assistants = [
            {
                'name': 'get_mobile_plans',
                'description': 'Mobile phone: Get a list of subscription plans.',
                'parameters': {'type': 'object', 'properties': {}},
                'returns': lambda arg: json.dumps([
                    {
                        'PlanId': 1,
                        'Name': 'Unlimited Plan',
                        'Description': 'Basic Fee:52 dollars, Data:Unlimited',
                        'BaseFee': 6480,
                        'CallFeePer30Seconds': 22,
                        'DataUsageLimit': -1,
                        'CallUsageLimit': -1,
                        'DataFeePerGB': 0,
                        'ListSuitedFor': [
                            'Watch video a lot.',
                            'Play games frequently'
                        ]
                    },
                    {
                        'PlanId': 2,
                        'Name': 'Basic Plan + 4GB',
                        'Description': 'Basic Fee:10 dollars, Data:4GB',
                        'BaseFee': 980,
                        'CallFeePer30Seconds': 22,
                        'DataUsageLimit': 4,
                        'CallUsageLimit': -1,
                        'DataFeePerGB': 500,
                        'ListSuitedFor': [
                            'Beginner',
                            "Who doesn't use much internet service"
                        ]
                    }
                ])
            },
            # Similar structure for other mobile assistant tools...
        ]

        self.tools_for_shop_assistants = [
            {
                'name': 'find_nearby_shops',
                'description': 'shop: Find nearby shop of the user.',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'location': {'type': 'string', 'description': 'location'}
                    }
                },
                'returns': lambda arg: json.dumps([
                    {
                        'StopId': 1,
                        'Name': f"{json.loads(arg)['location']} east store",
                        'BusinessHour': "Every day 11:00 to 20:00",
                        'Services': "Sell phones, Teach the basics of how to use phones"
                    }
                ])
            },
            # Similar structure for other shop assistant tools...
        ]

    def get_tools_for_assistant(self, name: str) -> List[Dict]:
        tools_definitions: ToolsDefinition = []
        tools_to_load = []

        if name == "GenericAssistant":
            tools_to_load = self.tools_for_generic_assistants
        elif name == "MobileAssistant":
            tools_to_load = self.tools_for_mobile_assistants
        elif name == "ShopAssistant":
            tools_to_load = self.tools_for_shop_assistants

        for tool in tools_to_load:
            tools_definitions.append({
                'type': 'function',
                'name': tool['name'],
                'parameters': tool['parameters'],
                'description': tool['description']
            })

        return tools_definitions

    async def get_tool_response(self, tool_name: str, parameters: str, call_id: str) -> Union[ItemCreateMessage, SessionUpdateMessage]:
        tools = self.tools_for_mobile_assistants + self.tools_for_generic_assistants + self.tools_for_shop_assistants
        content = await tools.find(lambda tool: tool['name'] == tool_name)['returns'](parameters)

        if content == "Assistant_MobileAssistant":
            return self.create_mobile_assistant_config_message()
        elif content == "Assistant_ShopAssistant":
            return self.create_shop_assistant_config_message()
        elif content == "Assistant_GenericAssistant":
            return self.create_generic_assistant_config_message()

        return {
            'type': 'conversation.item.create',
            'item': {
                'type': 'function_call_output',
                'call_id': call_id,
                'output': content
            }
        }

    def create_generic_assistant_config_message(self) -> SessionUpdateMessage:
        system_message = f"""
        ##Role
        You are an expert, well-training agent for support center.
        You are a native speaker of {self.language} without any accents.
        Use function calling to switch to specialized assistant.
        """

        return {
            'type': 'session.update',
            'session': {
                'turn_detection': {'type': 'server_vad'},
                'instructions': system_message,
                'tools': self.get_tools_for_assistant("GenericAssistant")
            }
        }

    def create_mobile_assistant_config_message(self) -> SessionUpdateMessage:
        system_message = f"""
        ## Role
        You are an expert agent for mobile phone contract questions.
        """

        return {
            'type': 'session.update',
            'session': {
                'turn_detection': {'type': 'server_vad'},
                'instructions': system_message,
                'tools': self.get_tools_for_assistant("MobileAssistant")
            }
        }

    def create_shop_assistant_config_message(self) -> SessionUpdateMessage:
        system_message = f"""
        ## Role
        You are an expert agent for shop-related questions.
        """

        return {
            'type': 'session.update',
            'session': {
                'turn_detection': {'type': 'server_vad'},
                'instructions': system_message,
                'tools': self.get_tools_for_assistant("ShopAssistant")
            }
        }
