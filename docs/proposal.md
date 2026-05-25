we have to write a proposal for a project.

here's the background for it:

the core idea/goal is this: an app/website that connects workers with customers.

lets take pov examples. from customer's pov, they want certain task to be done. it can be anything like fixing plumbing, fixing electrical, at-home barber service, quick pet checkup, mechanics service, etc. they simply define their needs and post a temporary job. they are then connected with the relevant worker through our app/website.

some narrower details:

customer has a location, after they post a job they get workers list and worker recommendation. only workers available in their city is shown unless wider zone is chosen. for workers within the city, the customer can see list of all available ones(workers). now based on certain criteria like locality, ratings, num of completed jobs the user gets recommendation for which worker to choose.

now from worker's pov,

they associate themselves with \#tags which identifies what jobs they can do.

they associate themselves with a location/zone/radius. if any relevant jobs are posted within that location/zone/radius they get notified about that job. worker also has the ability to see job posting outside their zone if they want to.

other features:

user can post a work requiring multiple workers, for eg: a whole house needs to be painted. they can either choose to group together multiple workers(select multiple workers) or they can simply choose the nearest professional organization/shop who sends their professionals instead.

eg: when a whole house needs to be painted user can group multiple people together. relevant material(paint) is discussed upon worker meetup. not much coordination is needed among the workers. they can simply decide who covers what areas.

but for a job requiring close communication/ relation and specific blueprint like doing plumbing for the whole house an organization is already capable and experienced to do so.

pricing: worker and client negotiate a deal.

based on job posted by the customer along with description, worker can give an initial estimate to the customer which play a factor on worker recommendation.

Problems:

certification/validation for workers: tbd

ui/ux detail: for worker think of the ui as a map. workers are located at a certain point represented by a red dot. a zone around worker is created which is their working zone any jobs posted around the zone appears as another point identifying the place of service. more tbd

//ai/ml integration chai, user le kaam vanxa, ani ai le automatic tags/workers suitable suggest garxa and manually ni milxa tags halna user side bata.

// aarko ranking/ worker suggestion ko ma ni halna milxa hola ai/ml or just kaam ko lagi kati paisa lagla- “suggestion” matrai, client offers, worker quotes. 

// aarko urgency ko hisaab le price higher, appointment reminder on both client and user side

// worker profile ma euta calender type ko ni banauna parle, appointments track/conflict herna. Dher complex nai, just timeline hernia milne gari. (User side ma ni calender ?)

//

### **Project Abstract**

* **Background & Problem:** While existing local service platforms (such as TaskRabbit or Thumbtack) connect users with professionals, they often restrict open price negotiation and struggle to handle both single ad-hoc tasks and complex multi-worker projects seamlessly. There is a significant gap for a highly localized, dynamic marketplace that gives users flexible hiring tiers and workers total geographic control.  
* **Objectives:** To develop a location-centric, tag-based application that directly connects customers with local gig workers and professional agencies, facilitating an open-market ecosystem for everyday services ranging from basic repairs to full-scale home renovations.  
* **Methodology:** The platform will utilize a map-based interface where workers define custom service radiuses and associate themselves with specific skill \#tags. Customers will post tasks and receive algorithmic recommendations based on proximity, ratings, and preliminary cost estimates. The core logic includes an open-negotiation pricing model and a scalable hiring feature, allowing users to hire an individual, group multiple independent workers for modular tasks (e.g., painting), or contract an agency for tightly coordinated projects (e.g., full plumbing).  
  * *// Comment: Insert brief details about your technical methodology here (e.g., "We will develop the platform using Agile methodology, utilizing \[Tech Stack\] for the frontend map UI and \[Database\] to handle real-time geospatial queries...").*  
* **Outcomes & Significance:** This platform will streamline local service fulfillment, empowering workers with autonomy over their zones and pricing, while providing customers with a transparent, highly customizable hiring experience.  
  * *// Comment: Insert your strategy for the "TBD" certification/validation gap here (e.g., "The platform will ensure user safety and quality control by implementing a \[background check / peer-reviewed validation / official certification upload\] system for all registered workers.").*

### **CHAPTER ONE: INTRODUCTION**

#### **1.1 Background**

* **The Gig Economy:** The demand for on-demand local services ranging from plumbing to pet care is growing rapidly.  
* **Current Landscape:** Platforms like TaskRabbit or Thumbtack exist, but they often act as strict middlemen.\`  
* **The Shift:** There is a growing need for a highly localized, flexible marketplace that allows workers to control their geographic reach via map-based interfaces and allows users to negotiate directly.

#### **1.2 Problem Statement**

* **Rigid Hiring Models:** Existing platforms handle single-task jobs well but fail when a customer needs multiple independent workers (e.g., painting a whole house) versus a highly coordinated agency (e.g., complete plumbing overhaul).  
* **Lack of Worker Autonomy:** Workers often cannot visually define custom service radiuses or negotiate pricing openly based on preliminary estimates.  
* **The Gap:** There is no unified platform that smoothly scales from a simple ad-hoc task to a multi-worker group project while keeping price negotiation and location matching fully transparent.  
* *// Comment: Insert specific local data or statistics here if your proposal requires backing up the market gap with hard numbers.*

#### **1.3 Objectives**

* To design a location-centric, map-based interface where workers define their service zones and receive real-time job notifications within that radius.  
* To implement a tag-based matching algorithm (\#tags) to connect customers with relevant skilled workers.  
* To build a flexible hiring framework supporting three tiers: single worker, multiple grouped independent workers, and professional agencies.  
* To develop a recommendation and bidding system based on locality, ratings, job completion history, and preliminary cost estimates.  
* *// Comment: Add a technical objective here, such as what frameworks or databases you aim to successfully deploy for the map UI or real-time notifications.*

#### **1.4 Significance of the Study**

* **For Customers:** Provides maximum flexibility. They can tailor their hiring approach (cheap independent group vs. premium agency) based on the task's complexity and negotiate prices directly.  
* **For Workers:** Empowers them with visual geographic control (map UI), direct negotiation power, and the ability to browse jobs outside their immediate zone if desired.  
* **For Local Economies:** Creates an open-market ecosystem that lowers barriers to entry for local gig workers while supporting established local professional shops.

#### **1.5 Scope and Limitations**

* **Scope:** The project covers the design and development of the dual-facing application (customer posting UI and worker map UI), the tag-based matching algorithm, the multi-tier hiring system, and the initial estimate/negotiation chat feature.  
* **Limitations:**  
  * *// Comment: Detail the certification/validation limitation here. For example: "The initial prototype will not include real-world background checks or legal validation of worker certificates, which remains a TBD feature for a live launch."*  
  * *// Comment: Add geographical limitations (e.g., "The initial testing phase will be restricted to \[City Name\]").*  
  * *// Comment: Note any payment gateway limitations if the app only handles negotiation but not the final secure money transfer.*

#### **1.6 Project Outline**

* **Chapter 1: Introduction** – Covers the project background, problem statement, objectives, and scope.  
* **Chapter 2: Literature Review** – Analyzes existing platforms, identifies the research gap, and reviews relevant technologies.  
* **Chapter 3: Methodology** – Details the system architecture, recommendation algorithm logic, and the development approach.  
* **Chapter 4: Implementation & Testing** – Describes the UI/UX design (including the worker map interface) and software testing phases.  
* **Chapter 5: Conclusion & Future Work** – Summarizes project outcomes and outlines future additions, such as the worker certification system.  
* *// Comment: Adjust these chapter titles if your university or organization requires a different standard structure.*

### **CHAPTER TWO: LITERATURE REVIEW**

#### **2.1 Related Work**

* **The Current Market:** The gig economy relies heavily on platforms that match users with local services. While successful, these systems often restrict how users and workers interact.  
* **The Research Gap:** Most literature and existing projects focus on 1-to-1 matching with fixed pricing models. There is limited focus on hybrid models that allow customers to choose between grouping independent workers or hiring a professional agency for the same project.

#### **2.1.1 Existing Gig Economy Platforms (e.g., TaskRabbit, Thumbtack)**

* **How They Work:** They allow users to post jobs and find local help for various tasks (plumbing, cleaning).  
* **Limitations:**  
  * They often dictate pricing or obscure the negotiation process.  
  * They lack a visual, map-based interface for workers to actively monitor and define their working zones.  
  * They do not easily support the "multi-worker group" feature for larger, modular tasks.

#### **2.1.2 Map-Based & Geospatial Service Systems (e.g., Uber, Delivery Apps)**

* **How They Work:** Utilize real-time GPS and map UIs to connect users with the nearest available service provider.  
* **Limitations:**  
  * These systems are designed for highly standardized tasks (driving, delivering), not diverse, skill-based jobs defined by \#tags.  
  * Workers cannot usually set custom, static service radiuses; they are constantly tracked dynamically.  
  * *// Comment: Add any specific local competitors or academic papers related to your specific region or market if required by your committee.*

#### **2.2 Theoretical Framework**

* **Geospatial Matching Theory:** The concept of connecting two parties based on overlapping location parameters. In this project, it involves plotting a "worker zone" (radius) against a "job location" point.  
* **Recommendation Systems:** Utilizing algorithms to sort and suggest workers. This project will weigh specific variables:  
  * Distance/Locality  
  * Relevance of \#tags  
  * Worker ratings and job completion history  
  * Initial cost estimate  
* **Platform Economics & Negotiation:** The theory of decentralized, open-market pricing where the platform provides the connection, but the worker and customer determine the final value.  
* *// Comment: If your course requires mathematical models or specific algorithm formulas (e.g., Haversine formula for distance), they should be detailed here.*

#### **2.3 Technology Review**

* **Mapping and Location Services:** Tools required to build the core UI (the red dot and worker zone).  
  * *// Comment: Specify technologies here once decided (e.g., Google Maps API, Mapbox, or Leaflet for the frontend).*  
* **Database & Backend (Spatial Queries):** Systems capable of handling fast radius searches and matching users based on location.  
  * *// Comment: Mention your database choice here (e.g., PostgreSQL with PostGIS, or MongoDB's geospatial queries).*  
* **Frontend/App Development:** Frameworks needed to build a responsive interface for both the customer list-view and the worker map-view.  
  * *// Comment: State whether you will use React Native, Flutter, Swift, etc.*  
* **Real-time Communication:** Technologies required for the instant notification system and the negotiation chat between worker and customer.  
  * *// Comment: Specify tools here (e.g., WebSockets, Firebase, or Socket.io).*

### **CHAPTER THREE: METHODOLOGY**

#### **3.1 System Overview**

* **Approach:** We will use the Agile development methodology.  
* **Why Agile?** It allows for iterative development, enabling us to test and refine complex features like the map-based worker UI and the multi-tier hiring system (group vs. agency) continuously based on feedback.  
* **Phases:** Requirements gathering, UI/UX prototyping, sprint-based backend/frontend development, and iterative testing.

#### **3.2 System Architecture**

* **Structure:** A standard Client-Server architecture.  
* **Frontend (Client):** Dual interfaces—a list/form-based interface for Customers and a map-based dashboard for Workers.  
* **Backend (Server):** Handles business logic, the recommendation algorithm, and real-time WebSocket connections for chat/negotiation.  
* **Database:** A relational database with geospatial capabilities to manage locations and overlapping zones.  
* *\[Insert Figure: System Architecture Diagram\]*  
  * *// Comment: Draw a diagram showing Mobile/Web Apps communicating via REST API/WebSockets to a Backend Server, which connects to a Cloud Database.*

#### **3.3 Use Case Diagram**

* **Actors:** Customer, Independent Worker, Professional Agency.  
* **Key Use Cases (Customer):** Post temporary job, browse available workers, group multiple workers, choose an agency, negotiate price.  
* **Key Use Cases (Worker/Agency):** Set \#tags, define working radius (map UI), view job postings, send cost estimates, browse out-of-zone jobs.  
* *\[Insert Figure: Use Case Diagram\]*  
  * *// Comment: The diagram should visually map the actors to these specific actions.*

#### **3.4 Class Diagram**

* **Core Classes:**  
  * User (Base class) \-\> Inherited by Customer, Worker, and Agency.  
  * Job (Attributes: Title, Description, Location Point, Status).  
  * LocationZone (Attributes: Center Coordinates, Radius).  
  * Bid/Estimate (Attributes: Proposed Price, Message).  
  * Tag (Skill identifiers).  
* *\[Insert Figure: Class Diagram\]*  
  * *// Comment: Ensure relationships are shown, e.g., a Job can have multiple Bids; a Worker can have multiple Tags.*

#### **3.5 Sequence Diagram**

* **Main Scenario: Job Posting & Matching**  
  * Customer creates a Job with location and \#tags.  
  * System queries the Database for Workers whose defined radius overlaps the Job location and who have matching \#tags.  
  * System ranks results based on ratings and completed jobs.  
  * System pushes real-time notifications to matching Workers.  
  * Worker views the point on their map UI and sends an initial estimate.  
  * Customer reviews estimates and initiates negotiation.  
* *\[Insert Figure: Sequence Diagram\]*  
  * *// Comment: Draw the vertical lifelines for Customer, System, Database, and Worker based on these steps.*

#### **3.6 ER Diagram / Database Design**

* **Key Entities & Relationships:**  
  * **Users Table:** Stores basic profiles (1-to-Many with Jobs/Bids).  
  * **Jobs Table:** Stores job requests, containing geospatial Point data.  
  * **Worker\_Profiles Table:** Stores radius data and certification status (TBD).  
  * **Worker\_Tags (Join Table):** Many-to-Many relationship between Workers and available \#tags.  
  * **Bids/Negotiations Table:** Tracks the pricing offers linked to specific Jobs and Workers.  
* *\[Insert Figure: ER Diagram\]*

#### **3.7 Data Flow Diagram (DFD)**

* **Level 0 (Context Diagram):** Shows the external entities (Customer, Worker) interacting with the main "Gig Matching & Negotiation System."  
* **Level 1 DFD:** Breaks down the system into major sub-processes:  
  1. User Registration & Zone Setup  
  2. Job Posting & Tag Matching  
  3. Recommendation & Notification Engine  
  4. Bidding & Negotiation  
* *\[Insert Figure: Level 0 and Level 1 DFDs\]*

#### **3.8 Implementation Details**

* *// Comment: Since you are familiar with AWS (EC2, Elastic Beanstalk), I have tailored the backend recommendations to fit that infrastructure. Adjust the frontend/database tech if you have other preferences.*  
* **Frontend (Mobile/Web):** React Native or Flutter for cross-platform mobile apps. Integration with Google Maps API or Mapbox for the worker's map UI and zone creation.  
* **Backend:** Node.js (Express) or Python (Django/FastAPI) to handle the recommendation logic and matching.  
* **Database:** PostgreSQL with the **PostGIS** extension (crucial for handling the spatial queries to instantly match a job's point with a worker's defined radius).  
* **Cloud Hosting:** AWS Elastic Beanstalk for easy deployment of the backend, or AWS EC2 for customized server control.  
* **Real-Time Comms:** Socket.io or AWS API Gateway WebSockets for instant job notifications and the negotiation chat interface.

### **CHAPTER FOUR: RESULT AND DISCUSSION**

#### **4.1 System Testing**

* **Testing Methodology:** We will use a mix of Unit Testing (testing individual functions), Integration Testing (ensuring database, backend, and frontend work together), and User Acceptance Testing (UAT) with mock users.  
* **Key Test Cases:**  
  * **Test Case 1 (Geospatial Matching):** Customer posts a job at Location X. System correctly identifies only workers whose defined radius covers Location X.  
  * **Test Case 2 (Tag Filtering):** Customer requests a \#plumbing job. System filters out workers in the radius who only have \#painting tags.  
  * **Test Case 3 (Multi-Worker Grouping):** Customer successfully selects 3 independent painters for a single house-painting job.  
  * **Test Case 4 (Negotiation):** Worker submits an initial estimate; Customer and Worker successfully exchange messages in real-time.  
  * *// Comment: Detail the specific Pass/Fail results for these test cases once development is complete.*

#### **4.2 Results**

* **Customer Interface:** Successfully implemented a location-aware posting system that returns a recommended list of workers based on ratings, distance, and initial estimates.  
* **Worker Interface:** Successfully built a map-based UI where workers appear as a red dot and can visually drag/adjust their working zone. Job postings appear as distinct points on this map.  
* **Hiring Tiers:** The system seamlessly switches between single-worker hiring, multi-worker grouping, and professional agency selection.  
* *\[Insert Figure: Screenshot of Customer Job Posting and Recommendation List\]*  
* *\[Insert Figure: Screenshot of Worker Map UI showing the Red Dot, Working Zone, and Job Points\]*  
  * *// Comment: Add screenshots of the actual app interfaces here.*

#### **4.3 Performance Analysis and Validation**

* **Geospatial Query Speed:** The database (e.g., PostGIS) efficiently calculates distance and radius overlaps, returning matching workers in under a target time (e.g., \< 200ms).  
* **Real-Time Latency:** WebSocket connections deliver job notifications and negotiation chat messages instantly, ensuring a smooth bidding process.  
* **Validation Against Objectives:**  
  * Objective 1 (Map UI for workers) \-\> Achieved.  
  * Objective 2 (Tag-based matching) \-\> Achieved.  
  * Objective 3 (Flexible group/agency hiring) \-\> Achieved.  
  * Objective 4 (Open negotiation) \-\> Achieved.  
  * *// Comment: Insert actual load testing numbers here if your project requires quantitative performance metrics (e.g., "System successfully handled 500 concurrent users").*

#### **4.4 Discussion**

* **Solving the Core Problem:** The results show that the platform successfully bridges the gap between rigid gig apps and localized needs. Giving workers visual geographic control directly improves their ability to find relevant work.  
* **Flexibility vs. Simplicity:** Allowing customers to group independent workers or choose an agency provides unmatched flexibility. However, open negotiation may take slightly longer than fixed-price apps, which is a calculated trade-off for better pricing fairness.  
* **Addressing Limitations:**  
  * The platform currently relies on a peer-review rating system for trust.  
  * *// Comment: Discuss the "certification/validation: TBD" issue here. Explain how future versions must implement background checks or official license uploads to ensure customer safety, especially for high-risk jobs like electrical work.*

### **CHAPTER FIVE: CONCLUSIONS AND FURTHER WORK**

#### **5.1 Conclusions**

* **A Flexible Solution:** The platform successfully addresses the rigid nature of current gig economy apps by introducing a highly localized, map-based marketplace.  
* **Worker Autonomy:** By utilizing a map UI, workers are empowered to visually define their service zones, track local demands, and bid on jobs based on their specific \#tags.  
* **Customer Choice:** The system successfully introduces a multi-tier hiring model, allowing customers to easily switch between hiring single workers, grouping independent professionals, or contracting established agencies based on the project's scale.  
* **Fair Pricing:** The open negotiation and initial estimate features foster a transparent market where prices are dictated by the users, not a middleman algorithm.

#### **5.2 Further Work / Recommendations**

* **Worker Certification & Validation (TBD resolution):** The most critical next step is implementing a strict verification system. This includes integrating background checks and a portal for workers (especially in trades like plumbing/electrical) to upload official state or local licenses.  
* **In-App Secure Payments:** Moving beyond just the negotiation phase to include an escrow-like payment gateway (e.g., Stripe API) to protect both the worker's earnings and the customer's deposit.  
* **AI Price Estimation:** Using historical job data to suggest a "fair market price range" to customers before they post a job, helping to guide the negotiation process.  
* *// Comment: Add any specific future features you have in mind, such as expanding to new cities or adding a premium subscription for agencies.*

### **REFERENCES**

*// Comment: Below are placeholder references in IEEE format. You must replace these with the actual papers, books, or documentation you review for your project.*

\[1\] A. Smith and J. Doe, “Geospatial matching algorithms in the modern gig economy,” *Journal of Platform Economics*, vol. 12, no. 4, pp. 112–125, 2023\.

\[2\] R. Roe, “Designing intuitive map-based interfaces for mobile service workers,” in *Proc. Int. Conf. on Human-Computer Interaction*, San Francisco, USA, 2024, pp. 45–52.

\[3\] M. Johnson, *Spatial Databases and PostGIS: A Practical Guide*. New York, USA: TechPress, 2022\.

\[4\] AWS Documentation, "Deploying Node.js applications to Elastic Beanstalk," Amazon Web Services, 2025\. \[Online\]. Available: *// Comment: Insert URL*

### **APPENDIX A: Source Code**

*// Comment: Insert your actual code here. Below is an example snippet showing how the backend might query the database for workers within the customer's radius using PostGIS.*

SQL

/\* Example: Finding Workers matching a \#tag within a specific radius \*/

SELECT 

    w.worker\_id, 

    w.name, 

    w.rating,

    ST\_Distance(w.location, ST\_MakePoint($1, $2)::geography) as distance

FROM 

    worker\_profiles w

JOIN 

    worker\_tags wt ON w.worker\_id \= wt.worker\_id

WHERE 

    wt.tag\_name \= $3 \-- e.g., '\#plumbing'

    AND ST\_DWithin(w.location, ST\_MakePoint($1, $2)::geography, w.working\_radius)

ORDER BY 

    w.rating DESC, distance ASC

LIMIT 10;

### **APPENDIX B: User Manual**

#### **Installation Procedures**

*// Comment: Adjust these steps based on your actual tech stack.*

1. **Prerequisites:** Install Node.js, npm, and PostgreSQL (with PostGIS extension).  
2. **Database Setup:**  
   * Run the provided schema.sql file to create the necessary tables and spatial indexes.  
3. **Backend Server:**  
   * Navigate to the /backend folder.  
   * Run npm install to install dependencies.  
   * Configure the .env file with your Database credentials and Maps API keys.  
   * Run npm start to launch the server.  
4. **Frontend App:**  
   * Navigate to the /frontend folder.  
   * Run npm install followed by npm start (or standard build commands for React/Flutter) to launch the user interface.

#### **Operation Procedures**

* **For Customers:**  
  1. Create an account and navigate to the "Post a Job" dashboard.  
  2. Enter the job description, set the location, and add relevant \#tags.  
  3. Choose the hiring tier: Single Worker, Group, or Agency.  
  4. Review the recommended list and initial estimates, then click "Negotiate" to open the chat.  
* **For Workers:**  
  1. Create a profile and select your specialized \#tags.  
  2. Open the "Map Interface".  
  3. Your location is marked with a red dot. Drag the radius slider to define your working zone.  
  4. Tap on new job points that appear within your zone to read details and submit an initial estimate.

