import os
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from dotenv import load_dotenv

load_dotenv()

# --- Pydantic Models for Structured Output ---

class ItemExtraction(BaseModel):
    intent: str = Field(description="The intent of the user: 'ADD_ITEM', 'QUERY_STOCK', 'UPDATE_ITEM', or 'SELL_ITEM'")
    category: Optional[str] = Field(None, description="Category of the item (e.g., Smartphone, Laptop, Tablet)")
    model: Optional[str] = Field(None, description="Model name (e.g., iPhone 14 Pro, MacBook Air M2)")
    specs: Optional[Dict[str, Any]] = Field(None, description="Dictionary of specs (e.g., {'storage': '128GB', 'color': 'Blue'})")
    purchase_price: Optional[float] = Field(None, description="The purchase price mentioned")
    sale_price: Optional[float] = Field(None, description="The sale price mentioned")
    repair_cost: Optional[float] = Field(None, description="The repair cost mentioned")
    notes: Optional[str] = Field(None, description="Any additional notes provided by the user")
    query: Optional[str] = Field(None, description="The natural language query if intent is QUERY_STOCK")

class AIEngine:
    def __init__(self):
        self.llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)
        self.parser = PydanticOutputParser(pydantic_object=ItemExtraction)

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are an inventory management assistant for a tech reseller. "
                "Your job is to analyze user input and extract structured data.\n\n"
                "{format_instructions}"
            )),
            ("user", "{input}")
        ])

        self.chain = self.prompt | self.llm | self.parser

    def analyze_input(self, text: str) -> ItemExtraction:
        """Analyzes text and returns a structured ItemExtraction object."""
        return self.chain.invoke({
            "input": text,
            "format_instructions": self.parser.get_format_instructions()
        })
