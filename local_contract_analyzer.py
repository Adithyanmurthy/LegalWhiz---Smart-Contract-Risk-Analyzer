"""
openai_analyzer.py

This module handles the analysis of contract text to:
1. Identify risky clauses
2. Provide simple explanations of complex legal text
3. Answer questions about the contract

All analysis is performed locally without external API calls.
"""

import re
import json
from collections import defaultdict

# Risk category definitions with search patterns and explanations
RISK_CATEGORIES = {
    "Auto-renewal": {
        "patterns": [
            r"auto(?:matic(?:ally)?)?[\s-]*renew",
            r"renew(?:s|ed|al)?[\s\w]{1,30}auto(?:matic(?:ally)?)?",
            r"(?:shall|will|may)[\s\w]{1,30}renew(?:s|ed|al)?[\s\w]{1,30}(?:unless|without|except|if)[\s\w]{1,50}(?:notice|notif|cancel)",
            r"continue(?:s|d)?[\s\w]{1,30}(?:for|until|period|year|month)[\s\w]{1,30}(?:unless|without|except)",
        ],
        "explanation": "This clause automatically extends your contract for additional periods unless you take specific action to cancel it. You may be locked into unwanted renewals if you miss the cancellation window.",
        "simplified": "This means the contract will keep renewing automatically unless you specifically cancel it before the deadline."
    },
    "Termination penalties": {
        "patterns": [
            r"(?:terminat(?:e|ion|ing)|cancel(?:lation)?)[\s\w]{1,50}(?:fee|penalt|charg|pay)",
            r"(?:fee|penalt|charg|pay)[\s\w]{1,50}(?:terminat(?:e|ion|ing)|cancel(?:lation)?)",
            r"(?:early|prior|before)[\s\w]{1,30}(?:terminat(?:e|ion|ing)|cancel(?:lation)?)[\s\w]{1,50}(?:fee|penalt|charg|pay|liabl)",
            r"(?:liquidated damages|compensation)[\s\w]{1,50}(?:terminat(?:e|ion|ing)|cancel(?:lation)?)",
        ],
        "explanation": "This clause requires you to pay a penalty or fee if you terminate the contract early. This could result in unexpected costs if you need to end the agreement before its natural term.",
        "simplified": "If you end the contract early, you'll need to pay an extra fee or penalty."
    },
    "Liability limitations": {
        "patterns": [
            r"(?:limit(?:s|ed|ing|ation)?|cap(?:s|ped)?)[\s\w]{1,50}(?:liab(?:le|ility)|damages|responsib(?:le|ility))",
            r"(?:no|not|never)[\s\w]{1,30}(?:liab(?:le|ility)|damages|responsib(?:le|ility))",
            r"(?:disclaim(?:s|er)?|waive(?:s|r)?)[\s\w]{1,30}(?:liab(?:le|ility)|damages|warranty|warranties)",
            r"under no circumstances[\s\w]{1,50}(?:liab(?:le|ility)|damages|responsib(?:le|ility))",
        ],
        "explanation": "This clause limits or removes the other party's liability for damages, even if they're at fault. This may leave you without recourse if you suffer financial losses due to their actions or negligence.",
        "simplified": "The other party won't be fully responsible for damages they cause, limiting your ability to seek compensation if things go wrong."
    },
    "Indemnification": {
        "patterns": [
            r"indemnif(?:y|ication|ies)",
            r"hold[\s\w]{1,20}harmless",
            r"defend(?:s)?[\s\w]{1,30}(?:against|from|for)",
            r"protect(?:s)?[\s\w]{1,30}(?:against|from|for)[\s\w]{1,30}(?:claims|suits|actions|demands)",
        ],
        "explanation": "This clause requires you to defend the other party from third-party claims and cover their legal costs and damages. This could expose you to significant financial risk beyond the value of the contract itself.",
        "simplified": "You must pay for any legal problems the other party faces because of your actions, including their lawyer fees and any damages."
    },
    "Non-compete": {
        "patterns": [
            r"non[\s-]*compet(?:e|ition)",
            r"(?:shall|will|must)[\s\w]{1,30}not[\s\w]{1,50}compet(?:e|ing)",
            r"(?:refrain|abstain|forbidden|prohibited)[\s\w]{1,30}(?:compet(?:e|ing)|similar[\s\w]{1,20}business)",
            r"(?:restrict(?:ed|ion)?|limit(?:ed|ation)?)[\s\w]{1,30}(?:compet(?:e|ing)|similar[\s\w]{1,20}business)",
        ],
        "explanation": "This clause restricts your ability to work in similar roles or start competing businesses for a period of time. This could limit your future career options or business opportunities.",
        "simplified": "You can't work for competitors or start a similar business for a certain period, which may limit your future job options."
    },
    "Intellectual property rights": {
        "patterns": [
            r"(?:assign(?:s|ed|ment)?|transfer(?:s|red)?)[\s\w]{1,30}(?:intellectual property|IP|copyright|patent|trademark)",
            r"(?:ownership|rights?)[\s\w]{1,30}(?:intellectual property|IP|copyright|patent|trademark)",
            r"(?:work for hire|work(?:s)?[\s-]*made[\s-]*for[\s-]*hire)",
            r"(?:retain(?:s|ed)?|maintain(?:s|ed)?)[\s\w]{1,30}(?:intellectual property|IP|copyright|patent|trademark)",
        ],
        "explanation": "This clause determines who owns intellectual property created during the contract. You might be signing away rights to your work or creations without adequate compensation.",
        "simplified": "Any creative work or inventions you develop may belong to the other party, not you, even after the contract ends."
    },
    "Jurisdiction and governing law": {
        "patterns": [
            r"(?:govern(?:ed|ing)?|interpreted)[\s\w]{1,30}(?:laws?|statutes?)[\s\w]{1,30}(?:of|in)[\s\w]{1,20}([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)",
            r"jurisdiction[\s\w]{1,30}(?:of|in)[\s\w]{1,20}([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)",
            r"venue[\s\w]{1,30}(?:shall|will|must)[\s\w]{1,30}(?:be|in)[\s\w]{1,20}([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)",
            r"disputes?[\s\w]{1,30}(?:resolved|settled|adjudicated)[\s\w]{1,30}(?:in|by)[\s\w]{1,20}([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)",
        ],
        "explanation": "This clause specifies where and under which laws any disputes must be resolved. This could require you to litigate in a distant or unfavorable jurisdiction, increasing your costs.",
        "simplified": "If there's a legal dispute, you may have to go to court in a different location than where you live or do business, which could be expensive and inconvenient."
    },
    "Dispute resolution": {
        "patterns": [
            r"(?:arbitrat(?:e|ion)|mediat(?:e|ion))",
            r"alternative dispute resolution",
            r"ADR",
            r"(?:waive(?:s|r)?|relinquish(?:es)?)[\s\w]{1,50}(?:right|ability)[\s\w]{1,50}(?:jury|class action|court)",
        ],
        "explanation": "This clause requires disputes to be resolved through specific methods like arbitration rather than courts. This may limit your legal options and rights, such as the ability to participate in class actions.",
        "simplified": "If you have a complaint, you can't go to regular court but must use a private dispute process that might be less favorable to you."
    },
    "Change of terms": {
        "patterns": [
            r"(?:chang(?:e|es|ed|ing)|modif(?:y|ies|ied|ication)|amend(?:s|ed|ment)?)[\s\w]{1,50}(?:terms|provisions|conditions|agreement)[\s\w]{1,50}(?:at any time|without|unilateral|sole discretion)",
            r"(?:reserv(?:e|es|ed)|right)[\s\w]{1,50}(?:chang(?:e|es|ed|ing)|modif(?:y|ies|ied|ication)|amend(?:s|ed|ment)?)[\s\w]{1,50}(?:terms|provisions|conditions|agreement)",
            r"revised[\s\w]{1,30}(?:terms|provisions|conditions|agreement)[\s\w]{1,50}(?:post(?:s|ed|ing)|notif(?:y|ies|ication)|websit(?:e)?)",
        ],
        "explanation": "This clause allows the other party to change contract terms unilaterally with minimal notice. This creates uncertainty as terms you agreed to could be changed without your explicit consent.",
        "simplified": "The other party can change the contract terms whenever they want, often with little notice, and continuing to use their service means you accept these changes."
    },
    "Late payment penalties": {
        "patterns": [
            r"(?:late|overdue|past due)[\s\w]{1,30}(?:fee|charge|penalty|interest)",
            r"(?:fee|charge|penalty|interest)[\s\w]{1,30}(?:late|overdue|past due)",
            r"(?:failure|fails?)[\s\w]{1,30}(?:pay|payment)[\s\w]{1,30}(?:fee|charge|penalty|interest)",
            r"interest[\s\w]{1,30}(?:rate|percent|%)[\s\w]{1,30}([0-9]+)",
        ],
        "explanation": "This clause imposes additional charges or interest when payments are late. These can quickly accumulate and significantly increase your total costs if you face temporary cash flow issues.",
        "simplified": "If you pay late, you'll be charged extra fees or interest, which can add up quickly if you miss payment deadlines."
    },
    "Minimum commitment": {
        "patterns": [
            r"minimum[\s\w]{1,30}(?:purchase|spend|payment|fee|commitment|guarantee|volume)",
            r"(?:commit(?:s|ment)?|guarantee(?:s|d)?)[\s\w]{1,30}minimum[\s\w]{1,30}(?:purchase|spend|payment|fee|volume)",
            r"at least[\s\w]{1,30}(?:\$[0-9,.]+|[0-9]+\s*%)",
            r"(?:shortfall|make-up)[\s\w]{1,30}(?:fee|charge|payment)",
        ],
        "explanation": "This clause requires you to purchase or pay a minimum amount regardless of your actual needs. You may end up paying for unused services or products if your requirements change.",
        "simplified": "You must spend at least a certain amount, even if you don't use all the services or products, so you might pay for things you don't need."
    },
    "Data usage and privacy": {
        "patterns": [
            r"(?:collect(?:s|ed|ion)?|use(?:s|d)?|shar(?:e|es|ed|ing)|process(?:es|ed|ing)?)[\s\w]{1,50}(?:data|information|personal information)",
            r"(?:consent(?:s|ed|ing)?|agree(?:s|d|ment)?)[\s\w]{1,50}(?:collect(?:s|ed|ion)?|use(?:s|d)?|shar(?:e|es|ed|ing)|process(?:es|ed|ing)?)[\s\w]{1,50}(?:data|information)",
            r"(?:privacy[\s\w]{1,10}policy|data[\s\w]{1,10}policy)",
            r"third(?:[\s-])*part(?:y|ies)",
        ],
        "explanation": "This clause governs how your data can be collected, used, and shared. It may allow broader usage of your information than you'd expect, potentially compromising privacy or confidentiality.",
        "simplified": "The other party can collect and use your information in various ways, possibly sharing it with others or using it for marketing purposes."
    }
}

# Keywords for contract summary extraction
SUMMARY_KEYWORDS = {
    "Term and duration": [
        "term", "duration", "period", "effective date", "commencement", "expiration", "termination date"
    ],
    "Payment terms": [
        "payment", "fee", "price", "rate", "compensation", "invoice", "billing", "cost", "expense", "paid", "reimburse"
    ],
    "Termination conditions": [
        "terminat", "cancel", "end", "cease", "discontinue", "expir", "wind up", "withdraw", "notice period"
    ],
    "Renewal terms": [
        "renew", "extension", "continue", "prolong", "extend", "subsequent term", "successive term"
    ],
    "Dispute resolution": [
        "dispute", "arbitration", "mediation", "lawsuit", "litigation", "court", "jurisdiction", "venue", "governing law", "legal"
    ]
}

def calculate_risk_level(text, category):
    """
    Calculate risk level for a clause on a scale of 1-5.
    
    Args:
        text (str): The clause text
        category (str): The risk category
    
    Returns:
        int: Risk level from 1-5
    """
    text = text.lower()
    
    # Base risk level starts at 1
    risk_level = 1
    
    # Risk factors that increase the score
    risk_factors = {
        "Auto-renewal": {
            2: ["30 day", "thirty day", "monthly", "quarterly"],
            3: ["automatic", "shall renew", "will renew"],
            4: ["without notice", "without prior notice", "unless notified"],
            5: ["sole discretion", "no obligation to notify", "automatically renew"]
        },
        "Termination penalties": {
            2: ["fee", "charge", "payment"],
            3: ["penalty", "liquidated damages", "compensation"],
            4: ["immediately due", "full payment", "remaining balance"],
            5: ["non-refundable", "no refund", "forfeit", "waive right"]
        },
        "Liability limitations": {
            2: ["reasonable", "liability limited to", "cap on damages"],
            3: ["waives", "disclaims", "excludes liability"],
            4: ["no liability", "not liable", "in no event"],
            5: ["gross negligence", "all liability", "under no circumstances"]
        },
        "Indemnification": {
            2: ["indemnify", "hold harmless"],
            3: ["defend", "all costs", "all expenses"],
            4: ["third party claims", "attorneys' fees", "court costs"],
            5: ["unlimited", "unconditional", "sole discretion"]
        },
        "Non-compete": {
            2: ["restricted", "limited", "non-compete"],
            3: ["prohibited", "shall not", "must not"],
            4: ["worldwide", "all markets", "any capacity"],
            5: ["perpetual", "indefinite", "unrestricted scope"]
        },
        "Intellectual property rights": {
            2: ["license", "permission", "authorization"],
            3: ["ownership", "rights", "title"],
            4: ["assign", "transfer", "work for hire"],
            5: ["perpetual", "irrevocable", "worldwide"]
        },
        "Jurisdiction and governing law": {
            2: ["governing law", "jurisdiction"],
            3: ["exclusive jurisdiction", "venue"],
            4: ["waive objection", "consent to jurisdiction"],
            5: ["foreign jurisdiction", "inconvenient forum"]
        },
        "Dispute resolution": {
            2: ["arbitration", "mediation", "dispute resolution"],
            3: ["binding", "final", "no appeal"],
            4: ["waive right to jury", "class action waiver"],
            5: ["confidential proceedings", "limited discovery"]
        },
        "Change of terms": {
            2: ["modify", "amend", "update"],
            3: ["change", "revise", "alter"],
            4: ["sole discretion", "at any time", "without notice"],
            5: ["deemed acceptance", "continued use constitutes agreement"]
        },
        "Late payment penalties": {
            2: ["interest", "late fee", "additional charge"],
            3: ["compound", "accumulate", "accrue"],
            4: ["immediate termination", "acceleration", "all amounts due"],
            5: ["excessive rate", "maximum allowed by law"]
        },
        "Minimum commitment": {
            2: ["minimum", "at least", "not less than"],
            3: ["guarantee", "commit", "ensure"],
            4: ["shortfall", "make-up payment", "true-up"],
            5: ["non-refundable", "no credit", "forfeit"]
        },
        "Data usage and privacy": {
            2: ["collect", "use", "process"],
            3: ["share", "disclose", "transfer"],
            4: ["third party", "affiliates", "partners"],
            5: ["sell", "monetize", "unlimited rights"]
        }
    }
    
    # Check for risk factors by category
    if category in risk_factors:
        for level, keywords in risk_factors[category].items():
            for keyword in keywords:
                if keyword.lower() in text.lower():
                    risk_level = max(risk_level, level)
    
    # Length factor - longer clauses often hide more risks
    words = len(text.split())
    if words > 200:
        risk_level = min(5, risk_level + 1)
    elif words > 100:
        risk_level = min(5, risk_level + 0.5)
    
    # Round and return
    return round(risk_level)

def extract_clause_context(text, start_idx, end_idx, max_length=500):
    """
    Extract the full clause context given start and end indices of a match.
    
    Args:
        text (str): The full contract text
        start_idx (int): Start index of the match
        end_idx (int): End index of the match
        max_length (int): Maximum length of the extracted clause
    
    Returns:
        str: The extracted clause
    """
    # Define paragraph separators
    separators = ['\n\n', '\n', '. ', ';']
    
    # Start from the most reliable separator (paragraph break) and go down
    for separator in separators:
        # Find clause start (beginning of paragraph containing match)
        left_text = text[:start_idx]
        clause_start = left_text.rfind(separator)
        if clause_start == -1:
            clause_start = 0
        else:
            clause_start += len(separator)
        
        # Find clause end (end of paragraph containing match)
        right_text = text[end_idx:]
        clause_end = right_text.find(separator)
        if clause_end == -1:
            clause_end = len(right_text)
        
        # Extract the clause
        clause = text[clause_start:end_idx + clause_end]
        
        # If clause is too long, try a different separator or truncate
        if len(clause) <= max_length:
            return clause.strip()
    
    # If all separators result in too long clauses, truncate to max_length
    # Get context before match (up to max_length/2)
    pre_context = text[max(0, start_idx - max_length//2):start_idx]
    # Get context after match (up to max_length/2)
    post_context = text[end_idx:min(len(text), end_idx + max_length//2)]
    
    # Combine contexts
    return (pre_context + text[start_idx:end_idx] + post_context).strip()

def analyze_contract(contract_text):
    """
    Analyze the contract text to identify risky clauses.
    
    Args:
        contract_text (str): The extracted text from the contract document
        
    Returns:
        dict: A dictionary containing the analysis results
    """
    results = {
        "risky_clauses": [],
        "contract_summary": []
    }
    
    # Skip analysis if text is too short or likely not a contract
    if len(contract_text) < 100:
        results["contract_summary"].append("The provided document appears to be too short for analysis.")
        return results
    
    # Normalize text for analysis
    normalized_text = contract_text.replace('\r', ' ').replace('\t', ' ')
    
    # Identify risky clauses
    found_categories = set()
    for category, info in RISK_CATEGORIES.items():
        for pattern in info["patterns"]:
            matches = list(re.finditer(pattern, normalized_text, re.IGNORECASE))
            
            # If matches found and category not already processed
            if matches and category not in found_categories:
                found_categories.add(category)
                
                # Get the best match (typically the first, but could be enhanced)
                match = matches[0]
                
                # Extract the full clause context
                clause_text = extract_clause_context(
                    normalized_text, 
                    match.start(), 
                    match.end()
                )
                
                # Calculate risk level
                risk_level = calculate_risk_level(clause_text, category)
                
                # Add to results
                results["risky_clauses"].append({
                    "category": category,
                    "text": clause_text,
                    "explanation": info["explanation"],
                    "simplified": info.get("simplified", ""),
                    "risk_level": risk_level
                })
                
                # Only process the first match for each category
                break
    
    # Generate contract summary
    summary_points = extract_summary_points(normalized_text)
    if summary_points:
        results["contract_summary"] = summary_points
    else:
        results["contract_summary"] = ["Unable to generate summary due to insufficient content."]
    
    return results

def extract_summary_points(text, max_points=5):
    """
    Extract key summary points from the contract text.
    
    Args:
        text (str): The contract text
        max_points (int): Maximum number of summary points to extract
    
    Returns:
        list: Summary points extracted from the contract
    """
    summary_points = []
    
    # Split text into paragraphs
    paragraphs = re.split(r'\n\s*\n', text)
    
    # Store identified paragraphs by category with their scores
    categorized_paragraphs = defaultdict(list)
    
    # Score each paragraph for each category
    for para in paragraphs:
        # Skip very short paragraphs
        if len(para.strip()) < 40:
            continue
        
        para_lower = para.lower()
        
        for category, keywords in SUMMARY_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                matches = re.findall(r'\b' + keyword, para_lower, re.IGNORECASE)
                score += len(matches) * 2
            
            if score > 0:
                # Store score and original paragraph text
                categorized_paragraphs[category].append((score, para.strip()))
    
    # For each category, get the highest scoring paragraph
    for category, scored_paragraphs in categorized_paragraphs.items():
        if scored_paragraphs:
            # Sort by score, highest first
            scored_paragraphs.sort(reverse=True, key=lambda x: x[0])
            
            # Get the highest scoring paragraph
            best_para = scored_paragraphs[0][1]
            
            # Summarize the paragraph
            summary = summarize_paragraph(best_para, category)
            if summary:
                summary_points.append(summary)
    
    # Limit to max_points and return
    return summary_points[:max_points]

def summarize_paragraph(paragraph, category):
    """
    Create a concise summary of a paragraph based on its category.
    
    Args:
        paragraph (str): The paragraph to summarize
        category (str): The category of the paragraph
    
    Returns:
        str: A summary of the paragraph
    """
    # Limit paragraph length for processing
    if len(paragraph) > 300:
        # Find a good breaking point (end of sentence)
        end_idx = paragraph[:300].rfind('.')
        if end_idx == -1:
            end_idx = 300
        paragraph = paragraph[:end_idx+1]
    
    # Simple keyword-based summarization
    if category == "Term and duration":
        # Look for term length
        term_match = re.search(r'(\d+)[\s-]*(day|week|month|year|annual)', paragraph, re.IGNORECASE)
        if term_match:
            term = f"{term_match.group(1)} {term_match.group(2)}s"
            return f"Contract term is {term}."
        
        # Look for specific dates
        date_match = re.search(r'from\s*(.*?)\s*(?:to|until|through)\s*(.*?)(?:\.|\n|$)', paragraph, re.IGNORECASE)
        if date_match:
            return f"Contract period runs from {date_match.group(1)} to {date_match.group(2)}."
        
        # Generic term statement
        return f"Contract includes term and duration provisions."
        
    elif category == "Payment terms":
        # Look for payment frequency
        freq_match = re.search(r'(monthly|weekly|quarterly|annual|yearly)', paragraph, re.IGNORECASE)
        amount_match = re.search(r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', paragraph)
        
        if freq_match and amount_match:
            return f"Payment of {amount_match.group(0)} due {freq_match.group(1)}."
        elif amount_match:
            return f"Payment amount specified as {amount_match.group(0)}."
        elif freq_match:
            return f"Payments due {freq_match.group(1)}."
        
        # Generic payment statement
        return f"Contract specifies payment obligations and terms."
        
    elif category == "Termination conditions":
        # Look for notice period
        notice_match = re.search(r'(\d+)[\s-]*(day|week|month).*?notice', paragraph, re.IGNORECASE)
        if notice_match:
            return f"Termination requires {notice_match.group(1)} {notice_match.group(2)}s notice."
        
        # Look for termination rights
        if re.search(r'terminat.*without cause', paragraph, re.IGNORECASE):
            return "Contract may be terminated without cause."
        elif re.search(r'terminat.*for cause', paragraph, re.IGNORECASE):
            return "Contract may be terminated for cause only."
        
        # Generic termination statement
        return "Contract includes termination provisions and conditions."
        
    elif category == "Renewal terms":
        # Look for automatic renewal
        if re.search(r'auto(matic)?.*?renew', paragraph, re.IGNORECASE) or re.search(r'renew.*?auto(matic)?', paragraph, re.IGNORECASE):
            return "Contract renews automatically unless cancelled."
        
        # Look for renewal term
        renewal_match = re.search(r'renew.*?(\d+)[\s-]*(day|week|month|year)', paragraph, re.IGNORECASE)
        if renewal_match:
            return f"Contract may renew for {renewal_match.group(1)} {renewal_match.group(2)}s."
        
        # Generic renewal statement
        return "Contract includes renewal terms and conditions."
        
    elif category == "Dispute resolution":
        # Look for arbitration
        if re.search(r'arbitrat', paragraph, re.IGNORECASE):
            return "Disputes must be resolved through arbitration."
        
        # Look for jurisdiction
        jurisdiction_match = re.search(r'jurisdiction of\s*([^\.]+)', paragraph, re.IGNORECASE)
        if jurisdiction_match:
            return f"Disputes governed by jurisdiction of {jurisdiction_match.group(1)}."
        
        # Look for governing law
        law_match = re.search(r'govern.*laws?\s*of\s*([^\.]+)', paragraph, re.IGNORECASE)
        if law_match:
            return f"Contract governed by laws of {law_match.group(1)}."
        
        # Generic dispute statement
        return "Contract specifies dispute resolution procedures."
    
    # Generic summary for other categories
    return f"Contract includes provisions regarding {category.lower()}."

def get_simple_explanation(text):
    """
    Get a simple explanation of a complex legal text.
    
    Args:
        text (str): Complex legal text to explain
        
    Returns:
        str: Simple explanation
    """
    # Identify the category of this clause
    identified_category = None
    for category, info in RISK_CATEGORIES.items():
        for pattern in info["patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                identified_category = category
                break
        if identified_category:
            break
    
    # If category found, return its simplified explanation
    if identified_category and "simplified" in RISK_CATEGORIES[identified_category]:
        return RISK_CATEGORIES[identified_category]["simplified"]
    
    # Fallback - create a generic simplified explanation
    words = text.split()
    if len(words) > 100:
        return "This is a complex legal clause that may have important implications for your rights and obligations. Consider seeking legal advice for a complete understanding."
    
    # Very basic simplification for shorter clauses
    text = re.sub(r'shall', 'will', text, flags=re.IGNORECASE)
    text = re.sub(r'herein', 'in this document', text, flags=re.IGNORECASE)
    text = re.sub(r'hereto', 'to this document', text, flags=re.IGNORECASE)
    text = re.sub(r'hereby', 'by this document', text, flags=re.IGNORECASE)
    text = re.sub(r'hereinafter', 'from now on', text, flags=re.IGNORECASE)
    text = re.sub(r'therein', 'in that', text, flags=re.IGNORECASE)
    text = re.sub(r'therefrom', 'from that', text, flags=re.IGNORECASE)
    text = re.sub(r'thereto', 'to that', text, flags=re.IGNORECASE)
    text = re.sub(r'aforementioned', 'previously mentioned', text, flags=re.IGNORECASE)
    
    return "This clause means: " + text

def answer_question(question, contract_text):
    """
    Answer a specific question about the contract using the contract text.
    
    Args:
        question (str): The user's question about the contract
        contract_text (str): The full text of the contract
        
    Returns:
        str: Answer to the question
    """
    # Normalize question and text
    question_lower = question.lower()
    text_lower = contract_text.lower()
    
    # Initialize response
    response = "The contract doesn't provide specific information about this question."
    
    # Define common question patterns and search logic
    question_patterns = {
        # Termination related questions
        r'(terminat|cancel|end)': {
            'keywords': ['terminat', 'cancel', 'end', 'notic', 'period'],
            'extract_patterns': [
                r'(?:terminat|cancel|end)(?:ion|ing)?[\s\w]{1,100}(\d+)[\s-]*(day|week|month|year)',
                r'(?:termin|cancel|end)(?:ate|ation)?(?:.*?)(?:with|after|upon)[\s\w]{1,50}(\d+)[\s-]*(day|week|month|year)',
                r'(?:notice|period)[\s\w]{1,50}(?:terminat|cancel|end)[\s\w]{1,50}(\d+)[\s-]*(day|week|month|year)'
            ],
            'default': "The contract mentions termination provisions, but specific details about notice periods or conditions are not clearly stated."
        },
        
        # Payment related questions
        r'(payment|fee|cost|price|pay)': {
            'keywords': ['payment', 'fee', 'cost', 'price', 'pay', 'amount', 'rate'],
            'extract_patterns': [
                r'(?:payment|fee|cost|price)[\s\w]{1,50}\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
                r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)[\s\w]{1,50}(?:payment|fee|cost|price)',
                r'(?:payment|fee|cost|price)[\s\w]{1,50}(\d+)(?:\.\d+)?[\s\w]{1,10}(?:percent|%)'
            ],
            'default': "The contract mentions payment terms, but specific amounts or payment schedules are not clearly defined."
        },
        
        # Renewal related questions
        r'(renew|extension|extend)': {
            'keywords': ['renew', 'extension', 'extend', 'continu', 'prolong'],
            'extract_patterns': [
                r'(?:auto|automatic)(?:ally)?[\s\w]{1,50}(?:renew|extend|continu)(?:ed|al)?',
                r'(?:renew|extend|continu)(?:ed|al)?[\s\w]{1,50}(?:auto|automatic)(?:ally)?',
                r'(?:renew|extend|continu)(?:ed|al)?[\s\w]{1,50}(?:for|by|of)[\s\w]{1,20}(\d+)[\s-]*(day|week|month|year)'
            ],
            'default': "The contract mentions renewal provisions, but specific terms or conditions are not clearly stated."
        },
        
        # Liability related questions
        r'(liability|responsible|damage)': {
            'keywords': ['liability', 'responsible', 'damage', 'compensat', 'harmless'],
            'extract_patterns': [
                r'(?:limit|cap)[\s\w]{1,50}(?:liability|damages?)[\s\w]{1,50}\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
                r'(?:not|no)[\s\w]{1,30}(?:liable|responsible)[\s\w]{1,50}(?:for|in case of|in event of)',
                r'(?:liability|damage)[\s\w]{1,50}(?:limit|cap|exclude|waive)'
            ],
            'default': "The contract addresses liability provisions, but specific limitations or conditions are not clearly defined."
        },
        
        # Dispute related questions
        r'(dispute|disagree|conflict|arbitration|court)': {
            'keywords': ['dispute', 'disagree', 'conflict', 'arbitration', 'mediation', 'court', 'lawsuit'],
            'extract_patterns': [
                r'(?:dispute|disagree|conflict)[\s\w]{1,50}(?:resolve|settle)[\s\w]{1,50}(?:by|through|via)[\s\w]{1,20}(arbitration|mediation|court|litigation)',
                r'(?:arbitration|mediation|court|litigation)[\s\w]{1,50}(?:in|of|at)[\s\w]{1,20}([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)',
                r'(?:govern|interpret)[\s\w]{1,50}(?:laws?|statutes?)[\s\w]{1,20}(?:of|in)[\s\w]{1,20}([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)'
            ],
            'default': "The contract includes dispute resolution provisions, but specific methods or jurisdiction may not be clearly defined."
        }
    }
    
    # Check each question pattern
    for pattern, config in question_patterns.items():
        if re.search(pattern, question_lower):
            # First, find paragraphs that contain keywords related to this question
            relevant_paragraphs = []
            paragraphs = re.split(r'\n\s*\n', contract_text)
            
            for para in paragraphs:
                para_lower = para.lower()
                keyword_count = sum(1 for keyword in config['keywords'] if keyword in para_lower)
                if keyword_count > 0:
                    # Score paragraph by keyword density
                    score = keyword_count / (len(para.split()) + 1) * 1000
                    relevant_paragraphs.append((score, para))
            
            # Sort paragraphs by relevance score
            relevant_paragraphs.sort(reverse=True)
            
            # If we found relevant paragraphs
            if relevant_paragraphs:
                best_paragraph = relevant_paragraphs[0][1]
                
                # Try to extract specific information using patterns
                for extract_pattern in config['extract_patterns']:
                    match = re.search(extract_pattern, best_paragraph, re.IGNORECASE)
                    if match:
                        # Format response based on matched information
                        if pattern == r'(terminat|cancel|end)':
                            if len(match.groups()) >= 2:
                                period = f"{match.group(1)} {match.group(2)}s"
                                return f"According to the contract, termination requires a notice period of {period}."
                            else:
                                return f"The contract allows for termination. Relevant clause: '{best_paragraph[:100]}...'"
                                
                        elif pattern == r'(payment|fee|cost|price|pay)':
                            if "$" in best_paragraph:
                                return f"The contract mentions payment details: '{best_paragraph[:150]}...'"
                            else:
                                return f"The contract includes payment terms. Relevant information: '{best_paragraph[:150]}...'"
                                
                        elif pattern == r'(renew|extension|extend)':
                            if "auto" in best_paragraph.lower():
                                return f"The contract includes automatic renewal provisions. Relevant clause: '{best_paragraph[:150]}...'"
                            else:
                                return f"The contract addresses renewal terms. Relevant information: '{best_paragraph[:150]}...'"
                                
                        elif pattern == r'(liability|responsible|damage)':
                            if "not" in best_paragraph.lower() or "no" in best_paragraph.lower():
                                return f"The contract contains liability limitations. Relevant clause: '{best_paragraph[:150]}...'"
                            else:
                                return f"The contract addresses liability. Relevant information: '{best_paragraph[:150]}...'"
                                
                        elif pattern == r'(dispute|disagree|conflict|arbitration|court)':
                            if "arbitration" in best_paragraph.lower():
                                return f"Disputes under this contract are resolved through arbitration. Relevant clause: '{best_paragraph[:150]}...'"
                            else:
                                return f"The contract specifies dispute resolution procedures. Relevant clause: '{best_paragraph[:150]}...'"
                
                # If no specific extract pattern matched but we have relevant text
                return f"Based on the contract: '{best_paragraph[:200]}...'"
            
            # If no relevant paragraphs, use default response
            return config['default']
    
    # Check for specific terms/definition questions
    if "what is" in question_lower or "what are" in question_lower or "define" in question_lower or "meaning of" in question_lower:
        # Extract the term being asked about
        term_match = re.search(r'what (?:is|are) (?:the )?(?:meaning of |definition of )?["\']?([a-z\s]+)["\']?', question_lower)
        if not term_match:
            term_match = re.search(r'define ["\']?([a-z\s]+)["\']?', question_lower)
        if not term_match:
            term_match = re.search(r'meaning of ["\']?([a-z\s]+)["\']?', question_lower)
            
        if term_match:
            term = term_match.group(1).strip()
            
            # Look for definitions in the contract
            definition_patterns = [
                rf'["\']?{term}["\']?[\s\w]{{1,30}}means',
                rf'["\']?{term}["\']?[\s\w]{{1,30}}shall mean',
                rf'["\']?{term}["\']?[\s\w]{{1,30}}defined as',
                rf'["\']?{term}["\']?[\s\w]{{1,10}}["\']?[\s\w]{{1,30}}is defined',
                rf'"[^"]*{term}[^"]*"'
            ]
            
            for pattern in definition_patterns:
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    # Extract the relevant paragraph
                    start_idx = max(0, match.start() - 50)
                    end_idx = min(len(contract_text), match.end() + 200)
                    definition_text = contract_text[start_idx:end_idx]
                    
                    # Clean up the extract
                    definition_text = re.sub(r'\s+', ' ', definition_text)
                    if len(definition_text) > 300:
                        definition_text = definition_text[:297] + "..."
                        
                    return f"The contract defines '{term}' as follows: '{definition_text}'"
    
    # If no specific answer found, return the default response
    return response