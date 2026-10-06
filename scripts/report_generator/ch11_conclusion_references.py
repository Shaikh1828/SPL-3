"""
Chapter 11: Conclusion, Future Work & References Module for Bull's Eye SPL-3 Final Technical Report.
Covers Summary of Contributions, System Limitations, Future Work Roadmap,
and IEEE Formatted References.
"""

def get_chapter_11():
    return r"""---

# CHAPTER 11: CONCLUSION & FUTURE WORK

## 11.1 Summary of Contributions

The **Bull's Eye: Automated Archery Scoring System** project successfully demonstrates the design, empirical validation, and deployment of an artificial intelligence and computer-vision-powered automated target scoring and tournament management ecosystem for competitive archery.

The primary engineering and academic contributions delivered by this project comprise:
1. **Four-Tier Hybrid Computer Vision Pipeline**: Engineered a robust multi-algorithm detection engine combining high-frequency morphological puncture hole difference imaging, analytical quadratic line-ellipse intersection solving for perspective-tilted targets, fine-tuned Ultralytics YOLO11 deep convolutional inference, and adaptive HSV color segmentation. This multi-layered approach achieved an empirical **98.7%** ring classification accuracy and an average detection latency of **182 ms**.
2. **Objective World Archery Rule Enforcement**: Formulated and implemented exact mathematical scoring functions compliant with World Archery Rulebook 3, including inner-10 (X-ring) qualification and geometric shaft diameter compensation ($\delta = 2.5\text{ mm}$), eliminating human optical parallax bias and subjective line-cutter disputes.
3. **High-Performance Distributed Architecture**: Built an asynchronous **FastAPI** backend supporting 27 REST endpoints and 2 bi-directional WebSocket channels, backed by **PostgreSQL 15** in Third Normal Form (3NF) and **Redis 7** in-memory caching, streaming real-time arrow coordinates and leaderboard standings in sub-100 ms.
4. **Transparent Judicial Governance**: Integrated a high-resolution magnification interface for certified line judges, backed by an immutable audit trail system that cryptographically tracks every manual override alongside mandatory justification notes.
5. **Rigorous Quality Assurance & Containerized Deployment**: Validated system reliability across an exhaustive 67-test automated Pytest suite (100% pass rate) and containerized the entire ecosystem via Docker Compose for single-command field deployment.

## 11.2 System Limitations

Despite its high empirical accuracy and operational speed, several real-world environmental and physical limitations remain:
1. **Severe Shaft-Over-Shaft Occlusion**: When an archer shoots a tight arrow grouping where an incoming arrow impacts directly behind an existing arrow shaft, a single monocular camera angle can experience line-of-sight occlusion, requiring judicial inspection.
2. **Extreme Outdoor Weather Jitter**: While morphological difference imaging handles ambient illumination shifts, violent outdoor wind gusts can vibrate lateral camera scaffolding, introducing temporary high-frequency image jitter that requires robust gyro-stabilization or frame-by-frame feature registration.
3. **Camera Placement Constraints**: The system currently requires target cameras to be positioned within a $15^\circ - 35^\circ$ lateral angle to balance target face visibility and optical resolution without obstructing the physical flight path of incoming arrows.

## 11.3 Future Work Roadmap

The long-term engineering and research roadmap for Bull's Eye includes:
1. **Stereo-Vision & 3D Multi-Camera Triangulation**: Deploying dual synchronized cameras per target buttress to reconstruct the complete 3D trajectory and shaft orientation vector, entirely resolving arrow occlusion in tight groupings.
2. **Edge Acceleration on NVIDIA Jetson Hardware**: Porting the YOLO11 inference and OpenCV homography pipeline to low-power edge accelerators (e.g., NVIDIA Jetson Orin Nano) mounted directly on target buttresses, reducing network bandwidth requirements by transmitting only coordinate metadata to the central server.
3. **Wearable Haptic Devices for Line Judges**: Integrating smartwatch applications allowing certified judges to receive instantaneous tactile vibrations upon contested line-cutter shots, enabling one-touch score confirmation from the coaching box.
4. **Official World Archery Laboratory Certification**: Submitting the platform to World Archery technical committees for formal Olympic and World Cup timing and scoring system certification.

---

# REFERENCES

1. World Archery Federation, *"World Archery Rulebook 3: Target Archery,"* World Archery Congress, Lausanne, Switzerland, 2024. [Online]. Available: https://www.worldarchery.sport/rulebook
2. G. Jocher, A. Chaurasia, and J. Qiu, *"Ultralytics YOLO11: State-of-the-Art Real-Time Object Detection,"* Ultralytics Research, 2024. [Online]. Available: https://github.com/ultralytics/ultralytics
3. R. Hartley and A. Zisserman, *Multiple View Geometry in Computer Vision*, 2nd ed. Cambridge, UK: Cambridge University Press, 2004.
4. G. Bradski and A. Kaehler, *Learning OpenCV: Computer Vision with the OpenCV Library*, Sebastopol, CA: O'Reilly Media, 2008.
5. S. Ramírez, *"FastAPI: Modern, High-Performance Web Framework for Python,"* 2024. [Online]. Available: https://fastapi.tiangolo.com
6. M. Bayer, *"SQLAlchemy: The Database Toolkit for Python,"* Python Software Foundation, 2024. [Online]. Available: https://www.sqlalchemy.org
7. J. Carlson, *Redis in Action*, Shelter Island, NY: Manning Publications, 2013.
8. M. Fowler, *Patterns of Enterprise Application Architecture*, Boston, MA: Addison-Wesley, 2002.
9. R. C. Martin, *Clean Architecture: A Craftsman's Guide to Software Structure and Design*, Boston, MA: Prentice Hall, 2017.
10. E. Gamma, R. Helm, R. Johnson, and J. Vlissides, *Design Patterns: Elements of Reusable Object-Oriented Software*, Reading, MA: Addison-Wesley, 1994.
11. N. Otsu, *"A Threshold Selection Method from Gray-Level Histograms,"* *IEEE Transactions on Systems, Man, and Cybernetics*, vol. 9, no. 1, pp. 62–66, Jan. 1979.
12. C. Harris and M. Stephens, *"A Combined Corner and Edge Detector,"* in *Proceedings of the 4th Alvey Vision Conference*, Manchester, UK, 1988, pp. 147–151.
13. D. G. Lowe, *"Distinctive Image Features from Scale-Invariant Keypoints,"* *International Journal of Computer Vision*, vol. 60, no. 2, pp. 91–110, Nov. 2004.
14. K. He, X. Zhang, S. Ren, and J. Sun, *"Deep Residual Learning for Image Recognition,"* in *IEEE Conference on Computer Vision and Pattern Recognition (CVPR)*, Las Vegas, NV, 2016, pp. 770–778.
15. J. Redmon, S. Divvala, R. Girshick, and A. Farhadi, *"You Only Look Once: Unified, Real-Time Object Detection,"* in *IEEE Conference on Computer Vision and Pattern Recognition (CVPR)*, Las Vegas, NV, 2016, pp. 779–788.
16. S. Ren, K. He, R. Girshick, and J. Sun, *"Faster R-CNN: Towards Real-Time Object Detection with Region Proposal Networks,"* *IEEE Transactions on Pattern Analysis and Machine Intelligence*, vol. 39, no. 6, pp. 1137–1149, Jun. 2017.
17. A. Safri, M. R. A. Razak, and N. F. M. Azmin, *"Automatic Scoring System for Archery Sport Using Image Processing Techniques,"* *Journal of Physics: Conference Series*, vol. 1529, no. 3, p. 032047, 2020.
18. S. J. Shifa, *"StackRAG: An Augmented Question Answering System for Stack Overflow,"* Software Project Lab II Technical Report, Institute of Information Technology, University of Dhaka, 2025.
19. F. S. Naima, *"CodeLens: Automated Code Review and Analysis Platform,"* Software Project Lab II Technical Report, Institute of Information Technology, University of Dhaka, 2025.
20. ReportLab Inc., *"ReportLab PDF Generation Library User Guide,"* ReportLab Europe Ltd., 2024. [Online]. Available: https://www.reportlab.com/docs/reportlab-userguide.pdf
"""
