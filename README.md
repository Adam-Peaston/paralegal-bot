# paralegal-bot
The law is too inaccessible to the public, partly because the language is full of terms of art (jargon) and partly because there is just so much reading to do that people with day jobs could not possibly hope to adequately know where they stand in respect of the law. Both of these problems are eminently solvable now. Let's do that.

## The objective
Goal here is to obtain a modest corpus of legal precedent and to turn that corpus into a ChatBot that you can consult with for answers to your legal questions. To achieve this I'm going to use the technique of Retrieval Augmented Generation (RAG), using technologies like LangChain to store my corpus in vector-searchable format and Llama 2 prompted with context + query to produce natural language synthesis of the answer to the user.  

I am looking forward to experimenting with different prompting techniques for different base LLMs, and also seeing how well I can get the system to properly cite the relevant cases.
