"""Module implementation of the country info function for telegram bot."""

import os
import logging
from typing import List
import requests
import telebot
from telebot import types
from telebot.callback_data import CallbackData
from bot_func_abc import AtomicBotFunctionABC

class CountryInfoBotFunction(AtomicBotFunctionABC):
    """Implementation of country info function using SOAP API"""

    commands: List[str] = ["countries", "cinfo"]
    authors: List[str] = ["IHVH"]
    about: str = "Информация о странах через SOAP API"
    description: str = """Доступные команды:
    /countries - получить список стран
    /cinfo [код] - информация о стране
    
    Примеры:
    /countries
    /cinfo RU (для России)"""
    state: bool = True

    bot: telebot.TeleBot
    country_keyboard_factory: CallbackData
    SOAP_URL = "http://webservices.oorsprong.org/websamples.countryinfo/CountryInfoService.wso"

    def set_handlers(self, bot: telebot.TeleBot):
        """Set message handlers"""
        self.bot = bot
        self.country_keyboard_factory = CallbackData('action', prefix=self.commands[0])

        @bot.message_handler(commands=self.commands)
        def country_message_handler(message: types.Message):
            chat_id_msg = f"\nCHAT ID = {message.chat.id}"
            
            if len(message.text.split()) > 1:
                # Если передан код страны
                country_code = message.text.split()[1].upper()
                self.__send_country_info(message.chat.id, country_code)
            else:
                # Показываем меню
                msg = (
                    f"Запрос обработан в CountryInfoBotFunction! {chat_id_msg}\n"
                    f"USER ID = {message.from_user.id}"
                )
                bot.send_message(
                    text=msg, 
                    chat_id=message.chat.id, 
                    reply_markup=self.__gen_main_markup()
                )

        @bot.callback_query_handler(func=None, config=self.country_keyboard_factory.filter())
        def country_callback_handler(call: types.CallbackQuery):
            callback_data: dict = self.country_keyboard_factory.parse(callback_data=call.data)
            action = callback_data['action']

            match action:
                case 'list_countries':
                    self.__send_countries_list(call.message.chat.id)
                case 'force_reply':
                    force_reply = types.ForceReply(selective=False)
                    text = "Введите код страны (например, RU):"
                    bot.send_message(call.message.chat.id, text, reply_markup=force_reply)
                    bot.register_next_step_handler(call.message, self.__process_country_code)
                case _:
                    bot.answer_callback_query(call.id, "Неизвестное действие")

    def __gen_main_markup(self):
        markup = types.InlineKeyboardMarkup()
        markup.row_width = 2
        
        list_callback = self.country_keyboard_factory.new(action='list_countries')
        reply_callback = self.country_keyboard_factory.new(action='force_reply')
        
        markup.add(
            types.InlineKeyboardButton("Список стран", callback_data=list_callback),
            types.InlineKeyboardButton("Ввести код", callback_data=reply_callback)
        )
        return markup

    def __send_countries_list(self, chat_id):
        """Send list of countries"""
        soap_request = """<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
            <soap:Body>
                <ListOfCountryNamesByName xmlns="http://www.oorsprong.org/websamples.countryinfo"/>
            </soap:Body>
        </soap:Envelope>"""

        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://www.oorsprong.org/websamples.countryinfo/ListOfCountryNamesByName"
        }

        try:
            response = requests.post(self.SOAP_URL, data=soap_request, headers=headers)
            if response.status_code == 200:
                countries = self.__parse_countries(response.text)
                message = "Список стран:\n" + "\n".join(
                    f"{code}: {name}" for code, name in countries[:15]  # Ограничиваем 15 странами
                )
                self.bot.send_message(chat_id, message)
            else:
                self.bot.send_message(chat_id, "Ошибка при получении списка стран")
        except Exception as e:
            logging.error(f"Error getting countries list: {e}")
            self.bot.send_message(chat_id, "Произошла ошибка при запросе")

    def __send_country_info(self, chat_id, country_code):
        """Send country info by code"""
        soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
            <soap:Body>
                <FullCountryInfo xmlns="http://www.oorsprong.org/websamples.countryinfo">
                    <sCountryISOCode>{country_code}</sCountryISOCode>
                </FullCountryInfo>
            </soap:Body>
        </soap:Envelope>"""

        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://www.oorsprong.org/websamples.countryinfo/FullCountryInfo"
        }

        try:
            response = requests.post(self.SOAP_URL, data=soap_request, headers=headers)
            if response.status_code == 200:
                info = self.__parse_country_info(response.text)
                message = (
                    f"Страна: {info.get('name', 'N/A')}\n"
                    f"Столица: {info.get('capital', 'N/A')}\n"
                    f"Телефонный код: {info.get('phone', 'N/A')}\n"
                    f"Валюта: {info.get('currency', 'N/A')}"
                )
                self.bot.send_message(chat_id, message)
            else:
                self.bot.send_message(chat_id, f"Не найдена страна с кодом {country_code}")
        except Exception as e:
            logging.error(f"Error getting country info: {e}")
            self.bot.send_message(chat_id, "Произошла ошибка при запросе")

    def __process_country_code(self, message):
        """Process entered country code"""
        try:
            country_code = message.text.strip().upper()
            self.__send_country_info(message.chat.id, country_code)
        except Exception as e:
            logging.error(f"Error processing country code: {e}")
            self.bot.send_message(message.chat.id, "Некорректный код страны")

    def __parse_countries(self, xml_response):
        """Parse countries list from XML"""
        from xml.etree import ElementTree as ET
        
        try:
            root = ET.fromstring(xml_response)
            countries = []
            for country in root.findall('.//{http://www.oorsprong.org/websamples.countryinfo}tCountryCodeAndName'):
                code = country.find('{http://www.oorsprong.org/websamples.countryinfo}sISOCode').text
                name = country.find('{http://www.oorsprong.org/websamples.countryinfo}sName').text
                countries.append((code, name))
            return countries
        except Exception as e:
            logging.error(f"Error parsing countries: {e}")
            return []

    def __parse_country_info(self, xml_response):
        """Parse country info from XML"""
        from xml.etree import ElementTree as ET
        
        try:
            root = ET.fromstring(xml_response)
            info = {
                'name': root.find('.//{http://www.oorsprong.org/websamples.countryinfo}sName').text,
                'capital': root.find('.//{http://www.oorsprong.org/websamples.countryinfo}sCapitalCity').text,
                'phone': root.find('.//{http://www.oorsprong.org/websamples.countryinfo}sPhoneCode').text,
                'currency': root.find('.//{http://www.oorsprong.org/websamples.countryinfo}sCurrencyISOCode').text
            }
            return info
        except Exception as e:
            logging.error(f"Error parsing country info: {e}")
            return {}