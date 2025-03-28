# LegalWhiz - Smart Contract Risk Analyzer

A locally-run tool that analyzes legal contracts to identify risky clauses, provide simplified explanations, and answer contract-related questions - all without sending your sensitive legal documents to external services.

![LegalWhiz Screenshot](https://placeholder-for-screenshot.com/legalwhiz-screenshot.png)

## 🔍 Key Features

- **Automatic Risk Detection**: Identifies potentially problematic clauses such as auto-renewal, termination penalties, liability limitations, and more
- **Risk Level Scoring**: Assigns a risk level (1-5) to each clause based on severity
- **Simple Explanations**: Translates complex legal language into easy-to-understand terms
- **Contract Q&A**: Ask specific questions about your contract and get accurate answers
- **Privacy-First**: 100% local processing - no data leaves your machine
- **Modern UI**: Clean, intuitive dark-themed interface
- **Multiple File Formats**: Support for PDF and DOCX documents

## 🚀 Getting Started

### Prerequisites

- Python 3.7+
- Pip package manager

### Installation

1. Clone this repository:
```
git clone https://github.com/yourusername/legalwhiz.git
cd legalwhiz
```

2. Install required dependencies:
```
pip install -r requirements.txt
```

3. Run the application:
```
streamlit run app.py
```

4. Open your browser and navigate to the URL shown in the terminal (typically http://localhost:8501)

## 📚 How It Works

1. **Upload**: Select and upload a contract document (PDF or DOCX)
2. **Analysis**: LegalWhiz extracts text and analyzes the document locally
3. **Review**: View highlighted risky clauses with explanations and risk levels
4. **Interact**: Ask questions about specific provisions in your contract
5. **Understand**: Get clear explanations of complex legal language

## 🛠️ Technical Architecture

```
legalwhiz/
│
├── app.py                  ← Streamlit frontend
├── openai_analyzer.py      ← Contract analysis logic (local, no API calls)
├── azure_form_parser.py    ← Document text extraction
├── requirements.txt        ← Project dependencies
└── README.md               ← This file
```

### How the Analysis Works

LegalWhiz uses a pattern-matching approach to identify potentially risky clauses:

1. **Pattern Identification**: Regular expressions match common legal language patterns
2. **Context Extraction**: The full clause context is extracted, not just the matched text
3. **Risk Scoring**: Each clause is scored based on specific risk factors and language
4. **Summary Generation**: Key points are extracted from the document for a high-level overview
5. **Q&A Processing**: Questions are parsed and relevant document sections are extracted for answers

## 📋 Risk Categories

LegalWhiz identifies and explains these common risky contract elements:

- **Auto-renewal** - Clauses that automatically extend your contract
- **Termination penalties** - Fees for ending the contract early
- **Liability limitations** - Restrictions on the other party's responsibility
- **Indemnification** - Requirements to defend the other party from claims
- **Non-compete** - Restrictions on future business activities
- **Intellectual property rights** - Who owns the work product
- **Jurisdiction and governing law** - Where disputes must be resolved
- **Dispute resolution** - How conflicts are handled (arbitration, etc.)
- **Change of terms** - Ability to modify contract terms unilaterally
- **Late payment penalties** - Extra charges for missing payment deadlines
- **Minimum commitment** - Required spending regardless of usage
- **Data usage and privacy** - How your information can be used

## 🤔 FAQ

**Q: Does LegalWhiz send my contract data to any external services?**  
A: No. All analysis happens locally on your machine. Your documents never leave your computer.

**Q: Is LegalWhiz a substitute for legal advice?**  
A: No. While LegalWhiz can help identify potential issues in contracts, it's not a substitute for professional legal counsel. Always consult with a qualified attorney for legal advice.

**Q: What file formats are supported?**  
A: Currently, LegalWhiz supports PDF and DOCX (Microsoft Word) formats.

**Q: How accurate is the analysis?**  
A: LegalWhiz uses pattern matching to identify potential issues, but it may miss some clauses or incorrectly identify others. Always review the full contract carefully.

## 🔧 Customization

You can customize the risk patterns in `openai_analyzer.py` by modifying the `RISK_CATEGORIES` dictionary. Add new patterns or adjust existing ones to better match the types of contracts you typically review.

## 💼 Use Cases

- **Small Business Owners**: Review service agreements before signing
- **Freelancers**: Check client contracts for unfavorable terms
- **Startups**: Analyze vendor agreements quickly without legal costs
- **Legal Teams**: Initial screening of contracts to focus review efforts
- **Individuals**: Better understand rental agreements, terms of service, etc.

## ⚖️ License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built using Streamlit for the user interface
- Document parsing with PyPDF2 and python-docx
- Developed for the Microsoft Hackathon

---

*Note: LegalWhiz is a tool for identifying potentially problematic contract clauses. It is not a substitute for professional legal advice.*
